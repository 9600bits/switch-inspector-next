"""SSH 采集器：按厂商下发命令集，解析为结构化结果。

容错原则：
- 连接失败 → 整台 fail；
- 单条命令下发失败 / 解析失败 → 该项 unk，原始输出保留进报告，不影响其他项。
"""

from dataclasses import dataclass, field

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

import parsers
import rules

# 各厂商命令集：(条目key, 命令)
COMMANDS = {
    "huawei": [
        ("version", "display version"),
        ("cpu", "display cpu-usage"),
        ("memory", "display memory-usage"),
        ("temp", "display environment"),
        ("fanpower", "display device"),
        ("alarm", "display alarm active"),
        ("log", "display logbuffer"),
        ("ports", "display interface brief"),
        ("err_in", "display counters errors inbound"),
        ("err_out", "display counters errors outbound"),
    ],
    "hp_comware": [
        ("version", "display version"),
        ("cpu", "display cpu-usage summary"),
        ("memory", "display memory"),
        ("temp", "display environment"),
        ("fan", "display fan"),
        ("power", "display power"),
        ("alarm", "display alarm"),
        ("log", "display logbuffer reverse"),
        ("ports", "display interface brief"),
        ("err_in", "display counters errors inbound"),
        ("err_out", "display counters errors outbound"),
    ],
}

CONNECT_TIMEOUT = 15   # 秒
CMD_TIMEOUT = 30       # 秒


@dataclass
class ItemResult:
    key: str
    status: str = "unk"           # ok/warn/crit/info/unk
    display: str = ""             # 报告里显示的文本
    detail: object = None         # 结构化细节（端口列表、日志条目等）


@dataclass
class DeviceResult:
    device: object
    status: str = "ok"            # 整台设备的总体状态
    error: str = ""               # 连接失败原因
    items: dict = field(default_factory=dict)   # key -> ItemResult
    raws: dict = field(default_factory=dict)    # key -> 原始输出


def _safe_parse(vendor, key, raw):
    """解析单条原始输出，失败返回 None。"""
    if not raw:
        return None
    try:
        return parsers.parse(vendor, key, raw)
    except Exception:
        return None


def _evaluate(key, value):
    """按规则给单项定级并生成展示文本。返回 (status, display, detail)。"""
    if key == "version":
        parts = []
        if value.get("model"):
            parts.append(value["model"])
        if value.get("version"):
            parts.append(f"版本 {value['version']}")
        if value.get("uptime"):
            parts.append(f"已运行 {value['uptime']}")
        return ("ok" if parts else "unk"), ("｜".join(parts) or "未知"), None

    if key == "cpu":
        pct = value["pct"]
        return rules.eval_cpu(pct), f"{pct}%", pct

    if key == "memory":
        pct = value["pct"]
        return rules.eval_memory(pct), f"{pct}%", pct

    if key == "temp":
        readings = value["readings"]
        mx = max(r["temp"] for r in readings)
        n_bad = sum(1 for r in readings if r["abnormal"])
        disp = f"最高 {mx}℃（{len(readings)} 个传感器"
        disp += f"，{n_bad} 个异常）" if n_bad else "）"
        return rules.eval_temp(readings), disp, readings

    if key == "fanpower":
        units, found = value["units"], value["found"]
        bad = [u for u in units if u["state"].lower() in rules.BAD_UNIT_STATES]
        if not found:
            return "unk", "输出中未识别到风扇/电源槽位", units
        disp = f"{len(units)} 个风扇/电源单元正常" if not bad \
            else "异常：" + "、".join(f"{u['name']}({u['state']})" for u in bad)
        return ("crit" if bad else "ok"), disp, units

    if key == "alarm":
        entries = value["entries"]
        disp = "无活跃告警" if not entries else f"{len(entries)} 条活跃告警"
        return rules.eval_alarm(entries), disp, entries

    if key == "log":
        flagged = value["flagged"]
        disp = "最近日志无明显异常" if not flagged else f"{len(flagged)} 条警告级及以上日志"
        return rules.eval_log(flagged), disp, flagged

    if key == "ports":
        s = value
        disp = (f"共 {s['total']} 口：up {s['up']}｜管理关闭 {s['admin_down']}"
                f"｜链路down {s['link_down']}")
        return rules.eval_ports(s), disp, s

    return "unk", "未知条目", None


def inspect(device) -> DeviceResult:
    """巡检一台设备。永不抛异常——所有失败都体现在返回值里。"""
    result = DeviceResult(device=device)
    raws = {}   # 先初始化，保证任何异常路径下都可安全赋值
    conn_params = {
        "device_type": device.vendor,
        "host": device.host,
        "port": device.port,
        "username": device.username,
        "password": device.password,
        "timeout": CONNECT_TIMEOUT,
    }
    try:
        with ConnectHandler(**conn_params) as conn:
            # 1) 下发全部命令，收集原始输出
            raws = {}
            for key, cmd in COMMANDS[device.vendor]:
                try:
                    raws[key] = conn.send_command(cmd, read_timeout=CMD_TIMEOUT)
                except Exception as e:
                    result.items[key] = ItemResult(
                        key=key, status="unk", display=f"命令执行失败:{e}")

            # 2) 逐项解析 + 定级（华三的风扇/电源两条命令延后合并）
            for key, _cmd in COMMANDS[device.vendor]:
                if key in result.items:            # 命令执行失败已记录
                    continue
                if key in ("fan", "power"):        # 华三专用，循环外合并
                    continue
                if key in ("err_in", "err_out"):   # 错包在下面统一合并
                    continue
                value = _safe_parse(device.vendor, key, raws.get(key))
                if value is None:
                    result.items[key] = ItemResult(
                        key=key, status="unk", display="解析失败")
                    continue
                status, display, detail = _evaluate(key, value)
                result.items[key] = ItemResult(key, status, display, detail)

            # 3) 风扇/电源：华为来自 display device（上面已处理）；华三合并 fan+power
            if device.vendor == "hp_comware":
                merged = parsers.merge_fanpower(
                    _safe_parse(device.vendor, "fan", raws.get("fan")),
                    _safe_parse(device.vendor, "power", raws.get("power")))
                if merged["found"]:
                    status, display, detail = _evaluate("fanpower", merged)
                    result.items["fanpower"] = ItemResult(
                        "fanpower", status, display, detail)
                else:
                    result.items["fanpower"] = ItemResult(
                        "fanpower", "unk", "输出中未识别到风扇/电源槽位")

            # 4) 错包：入向 + 出向合并
            has_err_raw = bool(raws.get("err_in") or raws.get("err_out"))
            err_in = _safe_parse(device.vendor, "err_in", raws.get("err_in")) or {}
            err_out = _safe_parse(device.vendor, "err_out", raws.get("err_out")) or {}
            bad_ports = parsers.merge_errors(err_in, err_out)
            if not has_err_raw:
                result.items["errors"] = ItemResult(
                    "errors", "unk", "未采集到错包数据")
            elif not bad_ports:
                result.items["errors"] = ItemResult(
                    "errors", "ok", "各端口无错包计数")
            else:
                names = "、".join(b["port"] for b in bad_ports[:8])
                disp = f"{len(bad_ports)} 个端口存在错包：{names}" \
                       + ("…" if len(bad_ports) > 8 else "")
                result.items["errors"] = ItemResult(
                    "errors", rules.eval_errors(bad_ports), disp, bad_ports)

    except NetmikoAuthenticationException:
        result.status = "fail"
        result.error = "认证失败：用户名或密码错误"
        return result
    except NetmikoTimeoutException:
        result.status = "fail"
        result.error = "连接超时：设备不可达或 SSH 未开启"
        return result
    except Exception as e:
        result.status = "fail"
        result.error = f"连接失败：{type(e).__name__}: {e}"
        return result

    # 整体评级
    if result.status != "fail":
        levels = [it.status for it in result.items.values()]
        result.status = rules.overall(levels)

    result.raws = raws
    return result
