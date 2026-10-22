"""Offline tests for platform detection and vendor-specific pagination setup."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from devices import Device
from secure_collector import DEFAULT_COMMANDS, PAGING, SafetyError, inspect


VERSIONS = {
    "huawei": "Huawei Versatile Routing Platform\nVersion 8.200\nHUAWEI S5735 uptime is 1 day",
    "hp_comware": "H3C Comware Software, Version 7.1.070\nH3C S5130S uptime is 1 week",
}


class Fake:
    def __init__(self, version, *, reject_paging=False, prompt="SW1"):
        self.version = version
        self.reject_paging = reject_paging
        self.prompt = prompt
        self.commands = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def find_prompt(self):
        return f"<{self.prompt}>"

    def send_command(self, command, read_timeout=None):
        self.commands.append(command)
        if command == "display version":
            return self.version
        if self.reject_paging and command in PAGING.values():
            raise SafetyError("设备未接受临时分页设置，停止采集")
        return "read-only output"


@pytest.mark.parametrize("vendor", ["huawei", "hp_comware"])
def test_version_detection_precedes_vendor_paging_and_collection(vendor):
    conn = Fake(VERSIONS[vendor])
    # The stored asset vendor is intentionally wrong: display version wins.
    registered_vendor = "hp_comware" if vendor == "huawei" else "huawei"
    result = inspect(
        Device("sw", "192.0.2.1", registered_vendor, 22, "u", "p"),
        connector=lambda **kwargs: conn,
    )

    assert result.status == "ok"
    assert result.detected_vendor == vendor
    assert result.vendor == vendor
    assert "登记厂商与识别结果不一致" in result.error
    assert conn.commands == ["display version", PAGING[vendor], *DEFAULT_COMMANDS[vendor]]


def test_unknown_version_runs_no_paging_or_collection_commands():
    conn = Fake("Vendor firmware 1.0")

    result = inspect(
        Device("sw", "192.0.2.1", "huawei", 22, "u", "p"),
        connector=lambda **kwargs: conn,
    )

    assert result.status == "fail"
    assert conn.commands == ["display version"]


@pytest.mark.parametrize("vendor", ["huawei", "hp_comware"])
def test_paging_failure_stops_before_collection_commands(vendor):
    conn = Fake(VERSIONS[vendor], reject_paging=True)

    result = inspect(
        Device("sw", "192.0.2.1", vendor, 22, "u", "p"),
        connector=lambda **kwargs: conn,
    )

    assert result.status == "fail"
    assert conn.commands == ["display version", PAGING[vendor]]
