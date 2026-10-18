"""命令输出解析器：纯函数，文本进 → 结构化数据出。

设计原则：
- 每个解析器按顺序尝试多组正则候选，兼容不同型号/固件版本差异；
- 全部候选都不命中时抛 ValueError，由上层降级为“未知”并折叠原始输出，
  绝不让单条命令的解析失败影响整台设备巡检。
"""

import re


class ParseError(ValueError):
    pass


# ---------------- 版本 / 运行时间（华为、华三通用） ----------------
_VERSION_RE = re.compile(r"Version\s+([^,\n]+)", re.I)
_UPTIME_RE = re.compile(r"uptime is (.+)", re.I)
_MODEL_RE = re.compile(r"(?:HUAWEI|H3C|HP)\s+([\w\-]+)\s+uptime", re.I)


def parse_version(text):
    ver = _VERSION_RE.search(text)
    upt = _UPTIME_RE.search(text)
    mod = _MODEL_RE.search(text)
    if not ver and not upt:
        raise ParseError("未找到版本或运行时间信息")
    return {
        "version": ver.group(1).strip() if ver else None,
        "uptime": upt.group(1).strip() if upt else None,
        "model": mod.group(1).strip() if mod else None,
    }


# ---------------- CPU ----------------
_CPU_PATTERNS = [
    re.compile(r"CPU\s+usage[:=\s]*(\d+)\s*%", re.I),
    re.compile(r"(\d+)\s*%\s+in last 5 seconds", re.I),
    re.compile(r"^\s*\d+\s+\d+\s+(\d+)\s*%", re.M),  # 槽位表格形式
]


def parse_cpu(text):
    for pat in _CPU_PATTERNS:
        vals = [int(v) for v in pat.findall(text)]
        if vals:
            return {"pct": max(vals)}
    raise ParseError("未找到 CPU 占用率")


# ---------------- 内存 ----------------
_MEM_PCT_RE = re.compile(r"[Mm]emory\s+[Uu]sage[:=\s]*(\d+)\s*%")
_H3C_SYSMEM_RE = re.compile(
    r"System memory:\s*(\d+)\s+(\d+)\s+(\d+)", re.I)


def parse_memory_huawei(text):
    vals = [int(v) for v in _MEM_PCT_RE.findall(text)]
    if vals:
        return {"pct": max(vals)}
    raise ParseError("未找到内存占用率")


def parse_memory_h3c(text):
    m = _H3C_SYSMEM_RE.search(text)
    if m:
        total, used = int(m.group(1)), int(m.group(2))
        if total > 0:
            return {"pct": round(used * 100 / total)}
    # 兜底：Total / Used 键值对
    tot = re.search(r"Total[^:\n]*:\s*(\d+)", text, re.I)
    used = re.search(r"Used[^:\n]*:\s*(\d+)", text, re.I)
    if tot and used and int(tot.group(1)) > 0:
        return {"pct": round(int(used.group(1)) * 100 / int(tot.group(1)))}
    raise ParseError("未找到内存统计")


# ---------------- 温度 ----------------
_HW_ENV_RE = re.compile(
    r"^\s*(\S+)\s+(\S+)\s+(NORMAL|ABNORMAL)\s+(\d+)\s+", re.I | re.M)
_H3C_ENV_RE = re.compile(
    r"^\s*(\d+)\s+(\S+)\s+(-?\d+)\s+-?\d+\s+\d+\s+\d+\s*$", re.M)


def parse_env_huawei(text):
    readings = []
    for slot, sensor, status, temp in _HW_ENV_RE.findall(text):
        readings.append({
            "where": f"{slot}/{sensor}",
            "temp": int(temp),
            "abnormal": status.upper() == "ABNORMAL",
        })
    if not readings:
        raise ParseError("未找到温度传感器数据")
    return {"readings": readings}


def parse_env_h3c(text):
    readings = []
    for slot, sensor, temp in _H3C_ENV_RE.findall(text):
        readings.append({"where": f"{slot}/{sensor}", "temp": int(temp),
                         "abnormal": False})
    if not readings:
        raise ParseError("未找到温度传感器数据")
    return {"readings": readings}


# ---------------- 风扇 / 电源 ----------------
_HW_PWR_FAN_RE = re.compile(
    r"^\s*((?:PWR|FAN|POWER)[A-Z0-9]*)\s+\S+\s+(\S+)\s+(\S+)", re.I | re.M)
_H3C_FP_RE = re.compile(r"^\s*\d+\s+\d+\s+(Normal|Abnormal)\b", re.I | re.M)
_HW_BAD_STATES = ("absent", "abnormal", "off", "fault", "invalid", "notpresent")


def parse_device_huawei(text):
    """display device：提取 PWR/FAN 槽位状态（板卡行忽略）。"""
    units = []
    for name, _type, state in _HW_PWR_FAN_RE.findall(text):
        units.append({"name": name.upper(), "state": state})
    return {"units": units, "found": bool(units)}


def parse_fp_h3c(text):
    states = [s.lower() for s in _H3C_FP_RE.findall(text)]
    if not states:
        return {"units": [], "found": False}
    units = [{"name": f"单元{i + 1}", "state": s}
             for i, s in enumerate(states)]
    return {"units": units, "found": True}


def merge_fanpower(*fp_values):
    """合并多个风扇/电源解析结果（华三 display fan + display power）。"""
    units, found = [], False
    for v in fp_values:
        if v and v.get("found"):
            found = True
            units.extend(v.get("units", []))
    return {"units": units, "found": found}


# ---------------- 告警 / 日志 ----------------
_INFO_LINE_RE = re.compile(
    r"^[-=\s]*$|Info:|^Info\b|null|没有.{0,8}(告警|记录)", re.I)
_ALARM_LINE_RE = re.compile(
    r"(Critical|Major|Minor|Warning|紧急|重要|次要|警告)", re.I)


def parse_alarm(text):
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or _INFO_LINE_RE.search(line):
            continue
        if _ALARM_LINE_RE.search(line) or re.match(r"^\d+\s", line):
            entries.append(line)
    return {"entries": entries[:50]}


_LOG_SEV_RE = re.compile(r"/([1-7])/[A-Za-z][A-Za-z0-9_]*")


def parse_log(text, max_lines=50):
    flagged = []
    for line in text.splitlines():
        line = line.rstrip()
        m = _LOG_SEV_RE.search(line)
        if m and int(m.group(1)) <= 4:  # 1-4：critical/major/warning 级别
            flagged.append(line)
    return {"flagged": flagged[-max_lines:]}


# ---------------- 端口简表 ----------------
_PORT_NUM_RE = re.compile(r"\d+/\d+/\d+")


def _classify_phy(tok):
    s = tok.strip()
    low = s.lower()
    if s.startswith("*") or low == "adm":
        return "admin_down"
    if low == "up":
        return "up"
    if low == "down":
        return "link_down"
    return None


def parse_ports_brief(text):
    total = up = admin_down = link_down = 0
    notable = []
    for line in text.splitlines():
        toks = line.split()
        if toks and toks[0].endswith(":"):
            continue  # 跳过图例行 Link: ADM - ...
        if len(toks) < 2:
            continue
        name, phy = toks[0], toks[1]
        kind = _classify_phy(phy)
        if kind is None or not _PORT_NUM_RE.search(name) and not \
                re.match(r"^[A-Za-z]+[\d/]+$", name):
            continue
        total += 1
        if kind == "up":
            up += 1
        elif kind == "admin_down":
            admin_down += 1
        else:
            link_down += 1
            notable.append({"name": name, "phy": "down", "kind": "down"})
    if total == 0:
        raise ParseError("未解析到端口行")
    return {"total": total, "up": up, "admin_down": admin_down,
            "link_down": link_down, "notable": notable}


# ---------------- 错包统计表 ----------------
_ERR_ROW_RE = re.compile(
    r"^\s*([A-Za-z][\w\-./:]*\d[\w\-./:]*)\s+((?:\d+\s+)*\d+)\s*$", re.M)


def parse_errors_table(text):
    """通用错误计数表：接口名 + 一串数字列，返回 {接口: 非零错误合计}。"""
    bad = {}
    for port, nums in _ERR_ROW_RE.findall(text):
        vals = [int(x) for x in nums.split()]
        if not vals:
            continue
        s = sum(vals)
        if s > 0:
            bad.setdefault(port, 0)
            bad[port] += s
    return bad


def merge_errors(inbound, outbound):
    """合并入/出两个方向的错包统计。"""
    ports = sorted(set(inbound) | set(outbound))
    return [{"port": p, "inbound": inbound.get(p, 0),
             "outbound": outbound.get(p, 0)} for p in ports]


# ---------------- 分发 ----------------
REGISTRY = {
    ("huawei", "version"): parse_version,
    ("huawei", "cpu"): parse_cpu,
    ("huawei", "memory"): parse_memory_huawei,
    ("huawei", "temp"): parse_env_huawei,
    ("huawei", "fanpower"): parse_device_huawei,
    ("huawei", "alarm"): parse_alarm,
    ("huawei", "log"): parse_log,
    ("huawei", "ports"): parse_ports_brief,
    ("huawei", "err_in"): parse_errors_table,
    ("huawei", "err_out"): parse_errors_table,

    ("hp_comware", "version"): parse_version,
    ("hp_comware", "cpu"): parse_cpu,
    ("hp_comware", "memory"): parse_memory_h3c,
    ("hp_comware", "temp"): parse_env_h3c,
    ("hp_comware", "fan"): parse_fp_h3c,
    ("hp_comware", "power"): parse_fp_h3c,
    ("hp_comware", "alarm"): parse_alarm,
    ("hp_comware", "log"): parse_log,
    ("hp_comware", "ports"): parse_ports_brief,
    ("hp_comware", "err_in"): parse_errors_table,
    ("hp_comware", "err_out"): parse_errors_table,
}


def parse(vendor, key, text):
    fn = REGISTRY.get((vendor, key))
    if fn is None:
        raise ParseError(f"未注册的解析器: {vendor}/{key}")
    return fn(text)
