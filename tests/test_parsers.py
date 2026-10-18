"""解析器离线测试：无需真机、无需网络，直接运行：

    python tests/test_parsers.py
"""

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, str(Path(__file__).parent.parent))

import parsers
from collectors import _evaluate

PASS = 0
FAIL = []


def check(name, cond):
    global PASS
    if cond:
        PASS += 1
    else:
        FAIL.append(name)
        print(f"  ✗ {name}")


# ---------------- 华为样例 ----------------
HW_VERSION = """Huawei Versatile Routing Platform Software
VRP (R) software, Version 5.170 (S5700 V200R010C00SPC500)
Copyright (C) 2000-2014 Huawei Technologies Co., Ltd.
HUAWEI S5700-52C-EI uptime is 1024 days, 1 hour, 2 minutes
"""

HW_CPU = """ CPU usage: 35% most: 62%
"""

HW_MEM = """ Memory Usage: 42%
"""

HW_ENV = """ Temperature: 
-------------------------------------------------------------------------------
 Slot  Sensor    Status    Temp(C)  Warning(C)  Fatal(C) 
-------------------------------------------------------------------------------
 1     NORMAL-0  NORMAL    41       62          67        
 1     NORMAL-1  ABNORMAL  78       62          67        
"""

HW_DEVICE = """S5700-52C-EI's Device status:
Slot Sub  Type              Online    Power     Register     Primary   Role
---------------------------------------------------------------------------
1    --   S5700-52C-EI      Present   PowerOn   Registered   Master    NA
PWR1 --   POWER             Absent    --        Registered   NA        NA
FAN1 --   FAN               Present   --        Registered   NA        NA
"""

HW_ALARM_EMPTY = """Info: The active alarm information is null.
"""

HW_ALARM = """--------------------------------------------------------------------------------
Index  Level    Date/Time           Description                                  
--------------------------------------------------------------------------------
1      Major    2026-01-01 12:00:00 The power module in slot PWR1 failed.        
"""

HW_LOG = """Aug 22 2026 23:32:00+08:00 SW01 %%01IFNET/6/IF_STATE(l)[123]:Interface GigabitEthernet0/0/1 has turned into UP state.
Aug 22 2026 23:33:00+08:00 SW01 %%01IFNET/4/IF_STATE(l)[124]:Interface GigabitEthernet0/0/2 has turned into DOWN state. 
Aug 22 2026 23:34:00+08:00 SW01 %%01SSH/6/SSH_LOGIN(l)[125]:login succeeded.
"""

HW_PORTS = """PHY: Physical
*down: administratively down
^down: standby
(l): loopback
(s): spoofing
(b): BFD down
InUti/OutUti: input traffic rate/output traffic rate
Interface                   PHY    Protocol  InUti OutUti   
GigabitEthernet0/0/1        up     up        0.01% 0.02%    
GigabitEthernet0/0/2        down   down      0%    0%       
GigabitEthernet0/0/3        *down  down      0%    0%       
XGigabitEthernet0/0/1       up     up        10%   12%      
"""

HW_ERR = """Interface                CRCi    Aligni    Undersizei    CRCo
GigabitEthernet0/0/1      12      0         0             0
GigabitEthernet0/0/24     0       0         0             5
"""


def t_huawei():
    v = parsers.parse("huawei", "version", HW_VERSION)
    check("hw version", v["version"].startswith("5.170"))
    check("hw model", v["model"] == "S5700-52C-EI")
    check("hw uptime", "1024 days" in v["uptime"])

    c = parsers.parse("huawei", "cpu", HW_CPU)
    check("hw cpu", c["pct"] == 35)

    m = parsers.parse("huawei", "memory", HW_MEM)
    check("hw mem", m["pct"] == 42)

    e = parsers.parse("huawei", "temp", HW_ENV)
    check("hw env count", len(e["readings"]) == 2)
    check("hw env abnormal", any(r["abnormal"] for r in e["readings"]))

    d = parsers.parse("huawei", "fanpower", HW_DEVICE)
    check("hw fanpower found", d["found"])
    check("hw fanpower units", len(d["units"]) == 2)

    a = parsers.parse("huawei", "alarm", HW_ALARM_EMPTY)
    check("hw alarm empty", a["entries"] == [])
    a2 = parsers.parse("huawei", "alarm", HW_ALARM)
    check("hw alarm entries", len(a2["entries"]) == 1)

    lg = parsers.parse("huawei", "log", HW_LOG)
    check("hw log flagged", len(lg["flagged"]) == 1)
    check("hw log content", "turned into DOWN" in lg["flagged"][0])

    p = parsers.parse("huawei", "ports", HW_PORTS)
    check("ports total", p["total"] == 4)
    check("ports up", p["up"] == 2)
    check("ports admin_down", p["admin_down"] == 1)
    check("ports link_down", p["link_down"] == 1)

    err_in = parsers.parse("huawei", "err_in", HW_ERR)
    check("err ports", set(err_in) == {"GigabitEthernet0/0/1",
                                       "GigabitEthernet0/0/24"})
    merged = parsers.merge_errors(err_in, {})
    check("err sum", sum(m["inbound"] + m["outbound"] for m in merged) == 17)
    check("err per-port", merged[0]["inbound"] == 12)


# ---------------- 华三样例 ----------------
H3C_VERSION = """H3C Comware Platform Software
Comware Software, Version 7.1.075, ESS 2432
Copyright (c) 2004-2021 New H3C Technologies Co., Ltd.
H3C S5560X-EI uptime is 15 days, 3 hours, 20 minutes, 5 seconds
"""

H3C_CPU = """Slot 1:
CPU usage:  23%,  5 seconds ago: 21%,  1 minute ago: 20%
"""

H3C_MEM = """Memory statistics are measured in KB:
Slot 1:
    Total Used Free Shared Buffers Physical
System memory: 3766408 1938464 1827944 0 156552 3984384
"""

H3C_ENV = """ System temperature information:
 Slot  Sensor   Temperature LowerLimit WarningLimit AlarmLimit
 1     HotSpot  38          -5         65           90
 1     Inlet    30          -5         60           85
"""

H3C_FAN = """ Slot  FanNo  Status    Speed(Judge)  Speed(RPM)
 1     1      Normal    40%           6000
 1     2      Abnormal  --            --
"""

H3C_POWER = """ Slot  No.  Status    Mode   Type
 1     1    Normal    AC     650W
"""

H3C_PORTS = """Brief information on interfaces in route mode:
Link: ADM - administratively down; Stby - standby
Interface            Link Protocol Primary IP      Description
GE1/0/53             UP   --       --              --
Brief information on interfaces in bridge mode:
Link: ADM - administratively down; Stby - standby
Interface            Link Speed Duplex Type PVID Description
GE1/0/1              UP   auto  auto   A    1    --
GE1/0/2              DOWN auto  auto   A    1    --
GE1/0/3              ADM  auto  auto   A    1    --
"""


# 供端到端测试复用的高 CPU / 正常风扇 / 告警日志样例
H3C_CPU_HIGH = """Slot 1:
CPU usage:  96%,  5 seconds ago: 95%,  1 minute ago: 90%
"""

H3C_FAN_OK = """ Slot  FanNo  Status    Speed(Judge)  Speed(RPM)
 1     1      Normal    40%           6000
 1     2      Normal    45%           6500
"""

H3C_LOG = """%Jan  1 00:00:00:000 2026 SHELL/6/SHELL_LOGIN: admin logged in.
%Jan  1 00:01:00:000 2026 IFNET/4/INTERFACE_UPDOWN: GE1/0/2 link status is DOWN.
"""


def _h3c_err_sample():
    return "Interface            ErrErrors   Discards\nGE1/0/48             3           0\n"


def t_h3c():
    v = parsers.parse("hp_comware", "version", H3C_VERSION)
    check("h3c version", v["version"].startswith("7.1.075"))
    check("h3c model", v["model"] == "S5560X-EI")

    c = parsers.parse("hp_comware", "cpu", H3C_CPU)
    check("h3c cpu", c["pct"] == 23)

    m = parsers.parse("hp_comware", "memory", H3C_MEM)
    expect = round(1938464 * 100 / 3766408)
    check("h3c mem pct", m["pct"] == expect)

    e = parsers.parse("hp_comware", "temp", H3C_ENV)
    check("h3c env", len(e["readings"]) == 2 and e["readings"][0]["temp"] == 38)

    fan = parsers.parse("hp_comware", "fan", H3C_FAN)
    pwr = parsers.parse("hp_comware", "power", H3C_POWER)
    fp = parsers.merge_fanpower(fan, pwr)
    check("h3c fp units", len(fp["units"]) == 3)
    st, disp, detail = _evaluate("fanpower", fp)
    check("h3c fp crit", st == "crit")

    p = parsers.parse("hp_comware", "ports", H3C_PORTS)
    check("h3c ports total", p["total"] == 4)
    check("h3c ports up", p["up"] == 2)
    check("h3c ports adm", p["admin_down"] == 1)
    check("h3c ports down", p["link_down"] == 1)


# ---------------- 规则 ----------------
def t_rules():
    import rules
    check("cpu warn", rules.eval_cpu(85) == "warn")
    check("cpu crit", rules.eval_cpu(95) == "crit")
    check("cpu ok", rules.eval_cpu(50) == "ok")
    check("mem warn", rules.eval_memory(82) == "warn")
    check("temp warn", rules.eval_temp([{"temp": 63, "abnormal": False}]) == "warn")
    check("temp crit", rules.eval_temp([{"temp": 80, "abnormal": False}]) == "crit")
    check("overall worst", rules.overall(["ok", "warn"]) == "warn")
    check("overall crit", rules.overall(["ok", "warn", "crit"]) == "crit")
    check("overall ok", rules.overall(["ok", "info", "unk"]) == "ok")


if __name__ == "__main__":
    print("运行解析器离线测试…")
    t_huawei()
    t_h3c()
    t_rules()
    print(f"\n通过 {PASS} 项检查" + (f"，失败 {len(FAIL)} 项！" if FAIL else "，全部 OK ✓"))
    sys.exit(1 if FAIL else 0)
