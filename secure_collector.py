"""Strictly allowlisted, user-view-only Huawei/H3C read-only collection."""
from dataclasses import dataclass, field
import codecs
import re
import socket
import time
import paramiko

PAGING = {"huawei": "screen-length 0 temporary", "hp_comware": "screen-length disable"}
DEFAULT_COMMANDS = {
 "huawei": ["display current-configuration", "display cpu-usage", "display memory-usage", "display device"],
 "hp_comware": ["display current-configuration", "display cpu-usage summary", "display memory", "display fan", "display power"],
}
ANALYSIS_COMMANDS = {
    vendor: ["display environment", "display interface brief",
             "display alarm active" if vendor == "huawei" else "display alarm",
             "display logbuffer" if vendor == "huawei" else "display logbuffer reverse",
             "display counters errors inbound", "display counters errors outbound"]
    for vendor in DEFAULT_COMMANDS
}
for _vendor in DEFAULT_COMMANDS:
    DEFAULT_COMMANDS[_vendor].extend(ANALYSIS_COMMANDS[_vendor])
CLI_ERROR = re.compile(r"^\s*(?:Error\s*:|%\s*(?:Unrecognized|Unknown|Invalid|Incomplete)|(?:Unrecognized|Unknown|Invalid|Incomplete)\s+(?:command|parameter)|错误[:：]|无法识别)", re.I | re.M)
# Kept as a compatibility alias for integrations that imported the original constant.
COMMANDS = DEFAULT_COMMANDS
SN_COMMANDS = {"huawei": "display device esn", "hp_comware": "display device manuinfo"}
COMMAND_PREFIXES = ("display ", "show ")
_COMMAND_SEPARATORS = re.compile(r"[\r\n;|]|&&|\|\||`")
OUTPUT_LIMIT = 5_000_000
PAGE_LIMIT = 512
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_PAGE_TAIL = re.compile(r"(?:^|\n)[ \t]*(?:-{2,}[ \t]*More[ \t]*-{2,}|More:|按任意键继续|Press any key to continue)[ \t]*$", re.I)
CONSOLE_PAGING_NOTICE = "Console 不支持 VTY 临时分页设置，已启用自动翻页（不修改设备配置）"

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


def _connect_ssh_socket(host, port, timeout):
    """Verify a server SSH identification before sending data to a possible console.

    Peek rather than consume the banner: Paramiko must read it from the same socket.
    A TCP console (common on simulator port 2000) otherwise interprets SSH KEX as CLI.
    """
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            sock.settimeout(max(0.01, deadline - time.monotonic()))
            try:
                banner = sock.recv(8192, socket.MSG_PEEK)
            except socket.timeout:
                break
            if not banner:
                raise SafetyError("目标端口在 SSH 握手前关闭连接，请核对 SSH 服务及端口映射")
            # RFC 4253 permits informational lines before the SSH identification.
            if re.search(rb"(?:^|\n)SSH-(?:2\.0|1\.99)-[^\r\n]+\r?\n", banner):
                sock.settimeout(timeout)
                return sock
            if (b"\xff" in banner or re.search(
                    rb"(?:<[^<>\r\n]{1,128}>|(?:login|username|password)\s*:)", banner, re.I)):
                raise SafetyError("目标端口返回控制台/Telnet 提示，未发送 SSH 握手；请使用设备管理 IP 的 SSH 端口或其映射端口，勿使用模拟器 Console 端口")
            if re.search(rb"(?:^|\n)SSH-1\.[^\r\n]*\r?\n", banner):
                raise SafetyError("目标仅提供 SSH1，本应用需要 SSH2")
            if len(banner) >= 8192:
                raise SafetyError("目标端口未返回有效 SSH2 标识，请核对协议和端口")
            time.sleep(0.02)
        raise SafetyError("目标端口未在超时内返回 SSH2 标识，请核对 SSH 服务、协议和端口映射；模拟器 Console/Telnet 端口不能用于 SSH 巡检")
    except Exception:
        sock.close()
        raise


def _failure_message(exc):
    """Expose actionable categories, never raw network/auth exception strings."""
    if isinstance(exc, SafetyError):
        return f"SafetyError: {exc}"
    if isinstance(exc, paramiko.AuthenticationException):
        return "SSH 认证失败，请核对设备账户、密码及 SSH 登录权限"
    if isinstance(exc, paramiko.BadHostKeyException):
        return "SSH 主机密钥不匹配，请核对目标设备"
    if isinstance(exc, paramiko.ssh_exception.IncompatiblePeer):
        reason = str(exc).lower()
        algorithm = next((label for marker, label in (
            ("kex", "密钥交换"), ("host key", "主机密钥"),
            ("cipher", "加密"), ("mac", "消息校验")) if marker in reason), "协商")
        return f"SSH {algorithm}算法不兼容，请核对设备 SSH2 算法配置和固件版本"
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return "SSH 连接或读取超时，请核对管理 IP、端口映射和网络连通性"
    if isinstance(exc, (OSError, paramiko.ssh_exception.NoValidConnectionsError)):
        return "无法建立 TCP 连接，请核对管理 IP、SSH 端口、端口映射和防火墙"
    if isinstance(exc, paramiko.SSHException):
        reason = str(exc).lower()
        if "no acceptable" in reason:
            return "SSH 算法不兼容，请核对设备 SSH2 算法配置"
        if "banner" in reason:
            return "SSH 协议标识读取失败，请核对 SSH 服务、端口映射以及连接是否被设备关闭"
        if "incompatible version" in reason:
            return "SSH 协议版本不兼容，本应用需要 SSH2"
        if isinstance(exc, paramiko.ChannelException):
            return "SSH 终端通道被拒绝，请核对账户的 SSH 交互终端权限及设备会话数限制"
        if "pty" in reason:
            return "SSH 已连接，但设备拒绝终端分配请求，请核对账户终端权限"
        if "channel closed" in reason or "session" in reason:
            return "SSH 会话被设备关闭，请核对账户交互终端权限及设备 SSH 日志"
        return "SSH 握手或会话建立失败，请核对 CRT 是否使用 SSH2，以及双方连接的地址和端口是否一致"
    if isinstance(exc, EOFError):
        return "SSH 连接被对端关闭，请核对设备 SSH 日志、算法和会话数限制"
    return f"连接或采集失败 ({type(exc).__name__})"

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
    transport: str=""
    ssh_error: str=""
    pagination_mode: str=""
    command_status: dict=field(default_factory=dict)
    requested_commands: list=field(default_factory=list)

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
        self.socket = None
        stage = "TCP 连接与 SSH 协议检查"
        try:
            self.socket = _connect_ssh_socket(device.host, device.port, timeout)
            stage = "SSH 握手与认证"
            self.client.connect(hostname=device.host, port=device.port, username=device.username,
                                password=device.password, timeout=timeout, banner_timeout=timeout,
                                auth_timeout=timeout, look_for_keys=False, allow_agent=False,
                                sock=self.socket)
            stage = "SSH 交互终端建立"
            self.channel = self.client.invoke_shell()
            self.channel.settimeout(1.0)
            stage = "设备提示符读取"
            self._prompt = self._read_initial(timeout)
        except Exception as exc:
            self.close()
            if isinstance(exc, SafetyError):
                raise
            raise SafetyError(f"{stage}失败：{_failure_message(exc)}") from exc
    def _read_until_quiet(self, timeout, on_chunk=None):
        end=time.monotonic()+timeout; chunks=[]; last=time.monotonic(); size=0
        pending = ""
        pages = 0
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        while time.monotonic()<end:
            if self.channel.recv_ready():
                value=self.channel.recv(65536)
                if not value: raise SafetyError("设备在输出完成前关闭了连接")
                size+=len(value)
                if size>OUTPUT_LIMIT: raise SafetyError("命令输出超过安全上限，停止采集")
                text = decoder.decode(value)
                pending += text
                if on_chunk:
                    on_chunk(text)
                last=time.monotonic()
            elif pending and time.monotonic()-last>0.25:
                # Normalize terminal decorations only for pager/prompt detection.
                # Keep raw streaming events; the archived result excludes pager UI.
                text = _ANSI.sub("", pending).replace("\b", "").replace("\r", "")
                pager = _PAGE_TAIL.search(text)
                if pager and getattr(self, "_automatic_paging", False) and getattr(self, "_paging_command", False):
                    if pages >= PAGE_LIMIT:
                        raise SafetyError("自动翻页次数超过安全上限，停止采集")
                    chunks.append(text[:pager.start()])
                    pending = ""
                    pages += 1
                    # A single Space requests the next page; never send a CLI command.
                    self.channel.send(" ")
                    last = time.monotonic()
                    continue
                if re.search(r"(----\s*More\s*----|More:|按任意键继续|Press any key to continue)",text,re.I):
                    raise SafetyError("检测到分页提示，停止后续命令")
                lines=[line.strip() for line in text.replace("\r", "").splitlines() if line.strip()]
                if lines and re.fullmatch(r"(?:<[^<>\r\n]{1,128}>|\[[^\[\]\r\n]{1,128}\])", lines[-1]):
                    return "\n".join(chunks + [text])
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
        self._paging_command = command.lower().startswith(COMMAND_PREFIXES)
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
        if command == PAGING["huawei"] and re.fullmatch(
                r"\s*Error:\s*The type of the included user interface must be VTY\.?\s*", output, re.I):
            self._automatic_paging = True
            return output
        if command in PAGING.values() and re.search(r"(?:unrecognized|incomplete|unknown command|wrong parameter|error:|错误|无法识别)",output,re.I):
            raise SafetyError("设备未接受临时分页设置，停止采集")
        return output
    def close(self):
        try:
            if self.channel is not None:self.channel.close()
        finally:
            try:
                self.client.close()
            finally:
                if self.socket is not None:self.socket.close()
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
            command_sets=None, collect_sn=False, event_callback=None, telnet_connector=None):
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
            emit("command_error", command=command, error=_failure_message(exc))
            raise

    try:
        try:
            conn=connector(**params) if connector else ParamikoShell(device, connect_timeout)
            result.transport = "ssh"
        except Exception as ssh_exc:
            # Retry only connection/login establishment, never a collection command.
            # An explicit test/integration connector remains isolated unless a Telnet
            # connector is also supplied; production always enables this fallback.
            if connector is not None and telnet_connector is None:
                raise
            from telnet_shell import TelnetShell
            result.ssh_error = _failure_message(ssh_exc)
            emit("connection_fallback", transport="telnet", port=device.port,
                 message=f"SSH 登录失败：{result.ssh_error}；正在尝试同端口 Telnet ({device.port})")
            try:
                conn = (telnet_connector or TelnetShell)(device, connect_timeout)
                result.transport = "telnet"
                result.error = "SSH 登录失败，已自动使用 Telnet 采集（明文传输）"
            except Exception as telnet_exc:
                telnet_error = (_failure_message(telnet_exc) if isinstance(telnet_exc, SafetyError)
                                else "Telnet 连接或登录失败，请核对端口、账户及设备 Telnet 服务")
                raise SafetyError(f"SSH：{result.ssh_error}；Telnet：{telnet_error}") from telnet_exc
        with conn:
            _user_prompt(conn)
            emit("device_start", host=device.host, transport=result.transport)
            version_output = run_command(configured_vendor, "display version", allow_version=True)
            if len(version_output) > max_output: raise SafetyError("命令输出超过安全上限，停止采集")
            result.outputs["display version"] = version_output
            vendor = _identify_version(version_output)
            if vendor not in DEFAULT_COMMANDS:
                raise SafetyError("无法识别设备平台，已跳过厂商采集命令")
            result.vendor = result.detected_vendor = vendor
            if configured_vendor and configured_vendor != vendor:
                result.error += ("；" if result.error else "") + f"登记厂商与识别结果不一致，已按{vendor}命令执行"
            try:
                from parsers import parse_version
                details = parse_version(version_output)
                result.model, result.version, result.uptime = details.get("model") or "", details.get("version") or "", details.get("uptime") or ""
            except Exception:
                pass
            paging_output = run_command(vendor, PAGING[vendor])
            if CLI_ERROR.search(paging_output) and not getattr(conn, "_automatic_paging", False):
                raise SafetyError("设备未接受临时分页设置，停止采集")
            if getattr(conn, "_automatic_paging", False):
                result.pagination_mode = "automatic"
                result.outputs[PAGING[vendor]] = paging_output
                result.error += ("；" if result.error else "") + CONSOLE_PAGING_NOTICE
                emit("pagination_fallback", message=CONSOLE_PAGING_NOTICE)
            else:
                result.pagination_mode = "disabled"
            selected_sets = command_sets or DEFAULT_COMMANDS
            configured = selected_sets.get(vendor, DEFAULT_COMMANDS[vendor]) if isinstance(selected_sets, dict) else selected_sets
            rows = normalize_commands(configured)
            result.requested_commands = [row["command"] for row in rows if row["enabled"]]
            for row in rows:
                if not row["enabled"]: continue
                command = row["command"]
                value=run_command(vendor, command)
                if len(value)>max_output: raise SafetyError("命令输出超过安全上限，停止采集")
                result.outputs[command]=value
                result.command_status[command] = "unsupported" if CLI_ERROR.search(value) else "ok"
            if collect_sn:
                sn_command = SN_COMMANDS[vendor]
                try:
                    value = run_command(vendor, sn_command)
                    if len(value) > max_output: raise SafetyError("命令输出超过安全上限，停止采集")
                    result.outputs[sn_command] = value
                    result.serial_number = _serial_number(value)
                    if not result.serial_number:
                        result.error = (result.error + "；" if result.error else "") + "SN 未识别"
                except (SafetyError, OSError, paramiko.SSHException):
                    raise
                except Exception as exc:
                    result.error = (result.error + "；" if result.error else "") + "SN 未识别"
            emit("device_complete", host=device.host, status=result.status)
    except Exception as e:
        result.status="fail"
        result.error = _failure_message(e)
        emit("device_error", host=device.host, error=result.error)
    return result
