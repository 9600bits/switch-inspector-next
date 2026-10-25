"""Boundaries for Console pagination fallback, shared by SSH and Telnet shells."""
from collections import deque

import pytest

import secure_collector
from secure_collector import PAGING, ParamikoShell, SafetyError


class Pages:
    def __init__(self, pages):
        self.pages = deque(pages)
        self.parts = deque(self.pages.popleft())
        self.sent = []

    def recv_ready(self):
        return bool(self.parts)

    def recv(self, size):
        return self.parts.popleft()

    def send(self, text):
        self.sent.append(text)
        if text == " " and self.pages:
            self.parts.extend(self.pages.popleft())


def shell(pages, automatic=True):
    conn = object.__new__(ParamikoShell)
    conn.channel = Pages(pages)
    conn._automatic_paging = automatic
    conn._prompt = "<Huawei>"
    return conn


@pytest.mark.parametrize("error", [
    "Error: Unrecognized command", "Error: Permission denied", "Error: Wrong parameter",
    "Error: The type of the included user interface must be VTY.\nError: Permission denied",
])
def test_other_paging_errors_still_stop(error):
    conn = shell([[(PAGING["huawei"] + "\r\n" + error + "\r\n<Huawei>").encode()]], automatic=False)
    with pytest.raises(SafetyError, match="未接受临时分页"):
        conn.send_command(PAGING["huawei"])
    assert not conn._automatic_paging


def test_exact_vty_error_enables_paging_without_configuration_commands():
    conn = shell([[b"screen-length 0 temporary\r\nError: The type of the included user interface must be VTY.\r\n<Huawei>"]], automatic=False)
    output = conn.send_command(PAGING["huawei"])
    assert "must be VTY" in output and conn._automatic_paging
    assert conn.channel.sent == [PAGING["huawei"] + "\n"]


def test_no_pager_response_without_explicit_console_mode():
    conn = shell([[b"display device\r\n---- More ----"]], automatic=False)
    with pytest.raises(SafetyError, match="分页提示"):
        conn.send_command("display device", read_timeout=1)
    assert conn.channel.sent == ["display device\n"]


def test_repeated_pager_stops_at_page_limit(monkeypatch):
    monkeypatch.setattr(secure_collector, "PAGE_LIMIT", 2)
    conn = shell([[b"---- More ----"], [b"---- More ----"], [b"---- More ----"]])
    with pytest.raises(SafetyError, match="翻页次数超过"):
        conn.send_command("display device", read_timeout=2)
    assert conn.channel.sent == ["display device\n", " ", " "]


def test_missing_final_prompt_times_out_without_extra_input():
    conn = shell([[b"first\r\n---- More ----"], [b"last page without prompt"]])
    with pytest.raises(SafetyError, match="提示符超时"):
        conn.send_command("display device", read_timeout=.7)
    assert conn.channel.sent == ["display device\n", " "]


def test_output_limit_applies_across_pages(monkeypatch):
    monkeypatch.setattr(secure_collector, "OUTPUT_LIMIT", 35)
    conn = shell([[b"1234567890\r\n---- More ----"], [b"1234567890\r\n<Huawei>"]])
    with pytest.raises(SafetyError, match="输出超过"):
        conn.send_command("display device", read_timeout=2)


def test_complete_prompt_prevents_spurious_space_for_embedded_text():
    conn = shell([[b"display device\r\nText about More:\r\n<Huawei>"]])
    with pytest.raises(SafetyError, match="分页提示"):
        conn.send_command("display device", read_timeout=1)
    assert conn.channel.sent == ["display device\n"]


def test_configuration_prompt_after_pages_is_rejected():
    conn = shell([[b"first\r\n---- More ----"], [b"last\r\n[Huawei]"]])
    with pytest.raises(SafetyError, match="用户视图"):
        conn.send_command("display device", read_timeout=2)


def test_fragmented_pager_and_utf8_are_preserved_across_reads():
    content = "设备正常".encode()
    conn = shell([[b"display device\r\n" + content[:2], content[2:] + b"\r\n\x1b[7m---- Mo", b"re ----\x1b[0m"],
                  [b"\b\b\r\nlast\r\n<Huawei>"]])
    streamed = []
    output = conn.send_command("display device", read_timeout=2, on_chunk=streamed.append)
    assert "设备正常" in output and "last" in output
    assert "More" not in output and "\ufffd" not in output
    assert "设备正常" in "".join(streamed)
    assert conn.channel.sent == ["display device\n", " "]
