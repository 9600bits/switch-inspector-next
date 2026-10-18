"""端到端离线测试：伪造 SSH 连接输出，跑通 采集→解析→定级→HTML 全链路。

    python tests/test_e2e.py
"""

import re
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, str(Path(__file__).parent.parent))

import collectors
from devices import Device

PASS = 0
FAIL = []


def check(name, cond):
    global PASS
    if cond:
        PASS += 1
    else:
        FAIL.append(name)
        print(f"  ✗ {name}")


# ---------- 复用单元测试里的样例输出 ----------
sys.path.insert(0, str(Path(__file__).parent))
from test_parsers import (  # noqa: E402
    HW_ALARM_EMPTY, HW_CPU, HW_DEVICE, HW_ENV, HW_ERR, HW_LOG,
    HW_MEM, HW_PORTS, HW_VERSION,
    H3C_CPU_HIGH, H3C_ENV, H3C_FAN_OK, H3C_LOG, H3C_MEM, H3C_PORTS,
    H3C_POWER, H3C_VERSION, _h3c_err_sample,
)

HW_OUTPUTS = {
    "display version": HW_VERSION,
    "display cpu-usage": HW_CPU,
    "display memory-usage": HW_MEM,
    "display environment": HW_ENV,
    "display device": HW_DEVICE,
    "display alarm active": HW_ALARM_EMPTY,
    "display logbuffer": HW_LOG,
    "display interface brief": HW_PORTS,
    "display counters errors inbound": HW_ERR,
    "display counters errors outbound": "",
}


class FakeConn:
    def __init__(self, outputs):
        self._outputs = outputs

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def send_command(self, cmd, read_timeout=None):
        return self._outputs.get(cmd, "")


def install_fake(monkey_outputs_by_host, fail_hosts):
    def fake_connect(**params):
        host = params["host"]
        if host in fail_hosts:
            raise collectors.NetmikoTimeoutException()
        return FakeConn(monkey_outputs_by_host[host])
    collectors.ConnectHandler = fake_connect


def main():
    # 华三高 CPU 样例在 test_parsers 里没有常量，这里内联一份
    h3c_out = {
        "display version": H3C_VERSION,
        "display cpu-usage summary": H3C_CPU_HIGH,
        "display memory": H3C_MEM,
        "display environment": H3C_ENV,
        "display fan": H3C_FAN_OK,
        "display power": H3C_POWER,
        "display alarm": "",
        "display logbuffer reverse": H3C_LOG,
        "display interface brief": H3C_PORTS,
        "display counters errors inbound": _h3c_err_sample(),
        "display counters errors outbound": "",
    }
    install_fake({"192.168.1.1": HW_OUTPUTS, "192.168.1.2": h3c_out},
                 fail_hosts={"192.168.1.3"})

    dev_a = Device("核心A", "192.168.1.1", "huawei", 22, "x", "x", "总部")
    dev_b = Device("接入B", "192.168.1.2", "hp_comware", 22, "x", "x", "分支")
    dev_c = Device("离线C", "192.168.1.3", "huawei", 22, "x", "x", "分支")

    ra = collectors.inspect(dev_a)
    # 样例数据里故意埋了异常温度传感器(78℃ ABNORMAL) + 1 条警告日志
    check("A cpu ok", ra.items["cpu"].status == "ok")
    check("A temp crit(传感器ABNORMAL)", ra.items["temp"].status == "crit")
    check("A log warn", ra.items["log"].status == "warn")
    check("A overall crit", ra.status == "crit")

    rb = collectors.inspect(dev_b)
    check("B cpu crit(96%)", rb.items["cpu"].status == "crit")
    check("B fanpower ok", rb.items["fanpower"].status == "ok")
    check("B errors warn", rb.items["errors"].status == "warn")
    check("B overall crit", rb.status == "crit")

    rc = collectors.inspect(dev_c)
    check("C fail", rc.status == "fail")

    from report import build_html
    html = build_html([ra, rb, rc])
    check("html 含失联", "失联" in html)
    check("html 含设备名", "核心A" in html and "接入B" in html)
    check("html 含超时提示", bool(re.search(r"(连接超时|不可达)", html)))
    check("html 单文件无外链", "http://" not in html and "https://" not in html)

    tmp = Path(tempfile.mkdtemp()) / "report.html"
    tmp.write_text(html, encoding="utf-8")
    check("html 可写盘", tmp.exists() and tmp.stat().st_size > 3000)
    print(f"  报告样例已写到 {tmp}")

    print(f"\n通过 {PASS} 项检查" +
          (f"，失败 {len(FAIL)} 项！" if FAIL else "，全部 OK ✓"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
