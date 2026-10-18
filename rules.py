"""内置阈值与状态判定规则。

状态级别：
  ok    正常（绿）
  warn  警告（黄）
  crit  严重（红）
  info  提示（灰，非故障）
  unk   未知（灰，解析失败）
  fail  失联（深红，连接失败）
"""

# ---------------- 内置默认阈值 ----------------
CPU_WARN = 80
CPU_CRIT = 90
MEM_WARN = 80
MEM_CRIT = 90
TEMP_WARN = 60   # ℃
TEMP_CRIT = 75   # ℃

ITEM_LABELS = {
    "version":  "版本 / 运行时间",
    "cpu":      "CPU 占用率",
    "memory":   "内存占用率",
    "temp":     "温度",
    "fanpower": "风扇 / 电源",
    "alarm":    "当前活跃告警",
    "log":      "最近日志异常",
    "ports":    "端口状态",
    "errors":   "端口错包",
}

_LEVEL_ORDER = {"fail": 0, "crit": 1, "warn": 2, "ok": 3, "info": 4, "unk": 5}


def eval_cpu(pct):
    if pct is None:
        return "unk"
    if pct >= CPU_CRIT:
        return "crit"
    if pct >= CPU_WARN:
        return "warn"
    return "ok"


def eval_memory(pct):
    if pct is None:
        return "unk"
    if pct >= MEM_CRIT:
        return "crit"
    if pct >= MEM_WARN:
        return "warn"
    return "ok"


def eval_temp(readings):
    """readings: [{'temp': int, 'abnormal': bool}, ...]，空列表视为未知。"""
    if not readings:
        return "unk"
    if any(r.get("abnormal") for r in readings):
        return "crit"
    mx = max((r["temp"] for r in readings if isinstance(r.get("temp"), int)), default=None)
    if mx is None:
        return "unk"
    if mx >= TEMP_CRIT:
        return "crit"
    if mx >= TEMP_WARN:
        return "warn"
    return "ok"


def eval_fanpower(units, found):
    """units: [{'name','state'}]，found=False 表示输出里没识别到风扇/电源槽位。"""
    if not found or not units:
        return "unk"
    # 在位但状态异常的标红：state 含 abnormal / absent / off 等
    bad = [u["name"] for u in units if u["state"].lower() in BAD_UNIT_STATES]
    return "crit" if bad else "ok"


def eval_alarm(entries):
    if entries is None:
        return "unk"
    return "warn" if len(entries) > 0 else "ok"


def eval_log(flagged):
    if flagged is None:
        return "unk"
    return "warn" if len(flagged) > 0 else "ok"


def eval_ports(summary):
    """link-down（管理开启但链路断开）只是灰色提示，不算故障。"""
    if not summary or summary.get("total", 0) == 0:
        return "unk"
    return "ok"


def eval_errors(bad_ports):
    if bad_ports is None:
        return "unk"
    return "warn" if len(bad_ports) > 0 else "ok"


def overall(levels):
    """取最差级别；info/unk 不拉低整体评价。"""
    if "fail" in levels:
        return "fail"
    if "crit" in levels:
        return "crit"
    if "warn" in levels:
        return "warn"
    return "ok"


WORST_FIRST = sorted(_LEVEL_ORDER, key=_LEVEL_ORDER.get)


def worse(a, b):
    return a if _LEVEL_ORDER[a] <= _LEVEL_ORDER[b] else b


BAD_UNIT_STATES = ("absent", "abnormal", "off", "fault", "invalid", "notpresent")
