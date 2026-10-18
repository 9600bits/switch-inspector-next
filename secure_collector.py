"""Strictly allowlisted, user-view-only Huawei/H3C read-only collection."""
from dataclasses import dataclass, field
import re
import time
import paramiko

PAGING = {"huawei": "screen-length 0 temporary", "hp_comware": "screen-length disable"}
DEFAULT_COMMANDS = {
 "huawei": ["display current-configuration", "display cpu-usage", "display memory-usage", "display device"],
 "hp_comware": ["display current-configuration", "display cpu-usage summary", "display memory", "display fan", "display power"],
}
# Kept as a compatibility alias for integrations that imported the original constant.
COMMANDS = DEFAULT_COMMANDS
SN_COMMANDS = {"huawei": "display device esn", "hp_comware": "display device manuinfo"}
COMMAND_PREFIXES = ("display ", "show ")
_COMMAND_SEPARATORS = re.compile(r"[\r\n;|]|&&|\|\||`")

def validate_command(command):
    """Validate one user-view, read-only command without trying to parse CLI syntax."""
    if not isinstance(command, str):
        raise ValueError("命令必须是文本")
    value = command.strip()
    if not value or len(value) > 240 or not value.lower().startswith(COMMAND_PREFIXES):
        raise ValueError("命令必须以 display 或 show 开头")
    if _COMMAND_SEPARATORS.search(value) or value.startswith(("display  ", "show  ")):
        raise ValueError("命令只能是一行，不能包含命令拼接符")
    return value

def normalize_commands(commands):
    """Accept strings or {command, enabled} rows and return safe, ordered rows."""
    rows = []
    for item in commands or []:
        raw, enabled = (item, True) if isinstance(item, str) else (item.get("command", ""), item.get("enabled", True))
        value = validate_command(raw)
        if value not in [row["command"] for row in rows]:
            rows.append({"command": value, "enabled": bool(enabled)})
    if not rows:
        raise ValueError("至少保留一条采集命令")
    return rows
class SafetyError(RuntimeError): pass
@dataclass
class Collection:
    host: str
    vendor: str
    status: str="ok"
    error: str=""
    outputs: dict=field(default_factory=dict)
    detected_vendor: str=""
    model: str=""
    version: str=""
    uptime: str=""
    serial_number: str=""

def _user_prompt(conn):
    try: prompt = conn.find_prompt()
    except Exception as e: raise SafetyError("无法确认设备视图提示符") from e
    # VRP and Comware user views end in angle-bracket hostname. Reject privilege/config views.
    if not re.fullmatch(r"<[^<>\r\n]{1,128}>", prompt.strip()):
        raise SafetyError("拒绝执行：设备不在可确认的用户视图 <...>")

def _send(conn, vendor, command, timeout, allow_version=False, on_chunk=None):
    _user_prompt(conn)
    allowed = (vendor in PAGING and command == PAGING[vendor]) or allow_version or command.lower().startswith(COMMAND_PREFIXES)
    if not allowed: raise SafetyError("命令被安全白名单拒绝")
    if on_chunk is None:
        output = conn.send_command(command, read_timeout=timeout)
    else:
        try:
            output = conn.send_command(command, read_timeout=timeout, on_chunk=on_chunk)
        except TypeError as exc:
            # Older/test connectors do not expose the optional streaming hook.
            if "on_chunk" in str(exc):
                output = conn.send_command(command, read_timeout=timeout)
            else:
                raise
    if re.search(r"(----\s*More\s*----|More:|按任意键继续|Press any key to continue)", output, re.I):
        raise SafetyError("检测到分页提示，停止后续命令")
    return output

class ParamikoShell:
    """Raw interactive shell; avoids Netmiko's implicit terminal/paging commands."""
    def __init__(self, device, timeout):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.channel = None
        try:
            self.client.connect(hostname=device.host, port=device.port, username=device.username,
                                password=device.password, timeout=timeout, banner_timeout=timeout,
                                auth_timeout=timeout, look_for_keys=False, allow_agent=False)
            self.channel = self.client.invoke_shell()
            self.channel.settimeout(1.0)
            self._prompt = self._read_initial(timeout)
        except Exception:
            self.close()
            raise
    def _read_until_quiet(self, timeout, on_chunk=None):
        end=time.monotonic()+timeout; chunks=[]; last=time.monotonic(); size=0
        while time.monotonic()<end:
            if self.channel.recv_ready():
                value=self.channel.recv(65536)
                if not value: raise SafetyError("设备在输出完成前关闭了连接")
                size+=len(value)
                if size>5_000_000: raise SafetyError("命令输出超过安全上限，停止采集")
                text = value.decode("utf-8", "replace")
                chunks.append(text)
                if on_chunk:
                    on_chunk(text)
                last=time.monotonic()
            elif chunks and time.monotonic()-last>0.25:
                text="".join(chunks)
                if re.search(r"(----\s*More\s*----|More:|按任意键继续|Press any key to continue)",text,re.I):
                    raise SafetyError("检测到分页提示，停止后续命令")
                lines=[line.strip() for line in text.replace("\r", "").splitlines() if line.strip()]
                if lines and re.fullmatch(r"(?:<[^<>\r\n]{1,128}>|\[[^\[\]\r\n]{1,128}\])", lines[-1]):
                    return text
                time.sleep(0.05)
            else: time.sleep(0.05)
        raise SafetyError("等待完整输出及设备提示符超时，停止采集")
    def _read_initial(self, timeout):
        text=self._read_until_quiet(timeout)
        lines=[x.strip() for x in text.replace("\r","").splitlines() if x.strip()]
        if not lines: raise SafetyError("无法读取设备提示符")
        return lines[-1]
    def find_prompt(self): return self._prompt
    def send_command(self, command, read_timeout=60, on_chunk=None):
        self.channel.send(command+"\n")
        if on_chunk is None:
            text=self._read_until_quiet(read_timeout)
        else:
            try:
                text=self._read_until_quiet(read_timeout, on_chunk=on_chunk)
            except TypeError as exc:
                if "on_chunk" in str(exc):
                    text=self._read_until_quiet(read_timeout)
                else:
                    raise
        lines=text.replace("\r","").rstrip().splitlines()
        if lines:
            tail=lines[-1].strip()
            self._prompt=tail
            _user_prompt(self)
            lines.pop()
        if lines and lines[0].strip()==command: lines.pop(0)
        output="\n".join(lines)
        if command in PAGING.values() and re.search(r"(?:unrecognized|incomplete|unknown command|wrong parameter|error:|错误|无法识别)",output,re.I):
            raise SafetyError("设备未接受临时分页设置，停止采集")
        return output
    def close(self):
        try:
            if self.channel is not None:self.channel.close()
        finally:self.client.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

def _identify_version(text):
    lowered = text.lower()
    if "huawei" in lowered or "vrp" in lowered:
        return "huawei"
    if "h3c" in lowered or "comware" in lowered:
        return "hp_comware"
    return ""

def _serial_number(text):
    patterns = (r"(?:esn|serial(?: number)?|serialno|sn)\s*[:：#]?\s*([A-Za-z0-9][A-Za-z0-9._/-]{3,})",
                r"(?:设备序列号|序列号)\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9._/-]{3,})")
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return ""

def inspect(device, connector=None, connect_timeout=15, command_timeout=60, max_output=5_000_000,
            command_sets=None, collect_sn=False, event_callback=None):
    configured_vendor=device.vendor if device.vendor in DEFAULT_COMMANDS else ""
    result=Collection(device.host,configured_vendor)
    params={"device_type":configured_vendor or "generic", "host":device.host,"port":device.port,"username":device.username,"password":device.password,"timeout":connect_timeout}
    conn=None
    def emit(kind, **payload):
        if event_callback:
            try:
                event_callback(kind, **payload)
            except Exception:
                # UI telemetry must never interrupt device collection.
                pass

    def run_command(vendor, command, *, allow_version=False):
        emit("command_start", command=command)
        chunks = []
        def on_chunk(text):
            chunks.append(text)
            emit("output", command=command, chunk=text)
        try:
            value = _send(conn, vendor, command, command_timeout, allow_version=allow_version, on_chunk=on_chunk)
            if not chunks and value:
                emit("output", command=command, chunk=value)
            emit("command_complete", command=command)
            return value
        except Exception as exc:
            emit("command_error", command=command, error=str(exc))
            raise

    try:
        conn=connector(**params) if connector else ParamikoShell(device, connect_timeout)
        with conn:
            _user_prompt(conn)
            emit("device_start", host=device.host)
            version_output = run_command(configured_vendor, "display version", allow_version=True)
            if len(version_output) > max_output: raise SafetyError("命令输出超过安全上限，停止采集")
            result.outputs["display version"] = version_output
            vendor = _identify_version(version_output)
            if vendor not in DEFAULT_COMMANDS:
                raise SafetyError("无法识别设备平台，已跳过厂商采集命令")
            result.vendor = result.detected_vendor = vendor
            if configured_vendor and configured_vendor != vendor:
                result.error = f"登记厂商与识别结果不一致，已按{vendor}命令执行"
            try:
                from parsers import parse_version
                details = parse_version(version_output)
                result.model, result.version, result.uptime = details.get("model") or "", details.get("version") or "", details.get("uptime") or ""
            except Exception:
                pass
            run_command(vendor, PAGING[vendor])
            selected_sets = command_sets or DEFAULT_COMMANDS
            configured = selected_sets.get(vendor, DEFAULT_COMMANDS[vendor]) if isinstance(selected_sets, dict) else selected_sets
            rows = normalize_commands(configured)
            for row in rows:
                if not row["enabled"]: continue
                command = row["command"]
                value=run_command(vendor, command)
                if len(value)>max_output: raise SafetyError("命令输出超过安全上限，停止采集")
                result.outputs[command]=value
            if collect_sn:
                sn_command = SN_COMMANDS[vendor]
                try:
                    value = run_command(vendor, sn_command)
                    if len(value) > max_output: raise SafetyError("命令输出超过安全上限，停止采集")
                    result.outputs[sn_command] = value
                    result.serial_number = _serial_number(value)
                except Exception as exc:
                    result.error = (result.error + "；" if result.error else "") + "SN 未识别"
            emit("device_complete", host=device.host, status=result.status)
    except Exception as e:
        emit("device_error", host=device.host, error=str(e))
        result.status="fail"
        # Do not expose exception strings which may contain credentials.
        result.error=f"{type(e).__name__}: {e}" if isinstance(e,SafetyError) else f"连接或采集失败 ({type(e).__name__})"
    return result
