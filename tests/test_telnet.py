"""Automatic SSH -> Telnet on the same actual TCP port, using local servers."""
from contextlib import contextmanager
import socket
import threading
import time

import paramiko
import pytest

from devices import Device
from secure_collector import DEFAULT_COMMANDS, PAGING, SafetyError, inspect
from telnet_shell import TelnetChannel


@contextmanager
def telnet_device(mode="password", vendor="huawei", reject_paging=False, console_paging=False):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(2)
    listener.settimeout(8)
    state = {"commands": [], "credentials": [], "ssh_bytes": b"", "errors": [], "spaces": []}

    def serve():
        try:
            # First connection is the SSH banner probe: no SSH or credentials sent.
            with listener.accept()[0] as peer:
                peer.settimeout(5)
                peer.sendall(b"<Simulator>")
                try:
                    state["ssh_bytes"] = peer.recv(4096)
                except ConnectionResetError:
                    pass
            # A new connection to the SAME port now negotiates Telnet.
            with listener.accept()[0] as peer:
                peer.settimeout(5)
                reader = peer.makefile("rb")

                def line():
                    value = reader.readline()
                    if not value:
                        return None
                    # Consume the IAC option response before application data.
                    while len(value) >= 3 and value[0] == 255:
                        value = value[3:]
                    return value.decode().rstrip("\r\n")

                if mode == "enter":
                    peer.sendall(b"Press ENTER to get started.")
                    assert line() == ""
                    peer.sendall(b"<Switch>")
                elif mode == "console":
                    peer.sendall(b"<Switch>")
                elif mode == "config":
                    peer.sendall(b"[Switch]")
                elif mode == "silent":
                    while peer.recv(4096):
                        pass
                    return
                else:
                    # Deliberately split both IAC and the username/password prompts.
                    peer.sendall(b"\xff")
                    time.sleep(.02)
                    peer.sendall(b"\xfb\x01User")
                    time.sleep(.02)
                    peer.sendall(b"name: ")
                    state["credentials"].append(line())
                    peer.sendall(b"test-user\r\nPass")
                    time.sleep(.02)
                    peer.sendall(b"word: ")
                    state["credentials"].append(line())
                    if mode == "reject":
                        peer.sendall(b"Login incorrect\r\nUsername:")
                        try:
                            peer.recv(4096)
                        except ConnectionResetError:
                            pass
                        return
                    peer.sendall(b"test-password\r\n<Switch>")
                while True:
                    command = line()
                    if command is None:
                        break
                    state["commands"].append(command)
                    if command == "display version":
                        output = ("Huawei Versatile Routing Platform Version 8.200" if vendor == "huawei"
                                  else "H3C Comware Software, Version 7.1.070\nH3C S5130 uptime is 1 day")
                    elif console_paging and command == PAGING["huawei"]:
                        output = "Error: The type of the included user interface must be VTY."
                    elif console_paging and command == "display current-configuration":
                        peer.sendall((command + "\r\n#\r\nsysname Huawei\r\n\x1b[42D---- Mo").encode())
                        time.sleep(.02)
                        peer.sendall(b"re ----")
                        state["spaces"].append(reader.read(1))
                        peer.sendall(b"\b\b\b\b\b\b\b\b\b\b\b\b\b             \b\b\r\ninterface Vlanif1\r\n---- More ----")
                        state["spaces"].append(reader.read(1))
                        peer.sendall(b"\r\n ip address 192.0.2.1 255.255.255.0\r\nreturn\r\n<Switch>")
                        continue
                    elif reject_paging and command == PAGING[vendor]:
                        output = "Error: Unrecognized command"
                    else:
                        output = "safe output"
                    peer.sendall((command + "\r\n" + output + "\r\n<Switch>").encode())
                reader.close()
        except Exception as exc:
            state["errors"].append(exc)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1], state
    finally:
        thread.join(9)
        listener.close()
        assert not thread.is_alive()
        assert not state["errors"], state["errors"]


@pytest.mark.parametrize("vendor", ["huawei", "hp_comware"])
def test_real_same_port_fallback_and_command_routing(vendor):
    events = []
    with telnet_device(vendor=vendor) as (port, state):
        result = inspect(Device("sw", "127.0.0.1", "", port, "test-user", "test-password"),
                         connect_timeout=2, command_timeout=2,
                         event_callback=lambda kind, **payload: events.append((kind, payload)))
    assert result.status == "ok", result.error
    assert result.transport == "telnet"
    assert result.detected_vendor == vendor
    assert "SSH 登录失败" in result.error
    assert state["credentials"] == ["test-user", "test-password"]
    assert state["commands"] == ["display version", PAGING[vendor], *DEFAULT_COMMANDS[vendor]]
    assert state["ssh_bytes"] == b""
    assert events[0][0] == "connection_fallback"
    assert events[0][1]["port"] == port
    assert events[1] == ("device_start", {"host": "127.0.0.1", "transport": "telnet"})
    assert events[-1][0] == "device_complete"
    assert "test-user" not in str(events) + str(result)
    assert "test-password" not in str(events) + str(result)


@pytest.mark.parametrize("mode", ["console", "enter"])
def test_console_without_login_can_collect(mode):
    with telnet_device(mode=mode) as (port, state):
        result = inspect(Device("sim", "127.0.0.1", "", port, "u", "p"),
                         connect_timeout=2, command_timeout=2, command_sets={"huawei": ["display device"]})
    assert result.status == "ok", result.error
    assert result.transport == "telnet"
    assert state["credentials"] == []
    assert state["commands"] == ["display version", PAGING["huawei"], "display device"]


@pytest.mark.parametrize("mode, expected", [("reject", "Telnet 认证失败"), ("silent", "Telnet 登录超时"),
                                           ("config", "用户视图")])
def test_telnet_login_failure_timeout_and_unsafe_view_send_no_collection(mode, expected):
    with telnet_device(mode=mode) as (port, state):
        result = inspect(Device("sw", "127.0.0.1", "", port, "test-user", "test-password"),
                         connect_timeout=.7, command_timeout=1)
    assert result.status == "fail"
    assert expected in result.error
    assert state["commands"] == []
    assert "test-password" not in str(result)
    if mode != "config":
        assert "SSH：" in result.error and "Telnet：" in result.error


def test_failed_paging_over_telnet_does_not_continue_collection():
    with telnet_device(reject_paging=True) as (port, state):
        result = inspect(Device("sw", "127.0.0.1", "", port, "test-user", "test-password"),
                         connect_timeout=2, command_timeout=2)
    assert result.status == "fail"
    assert state["commands"] == ["display version", PAGING["huawei"]]


def test_huawei_console_vty_error_switches_to_bounded_automatic_paging():
    events = []
    with telnet_device(mode="console", console_paging=True) as (port, state):
        result = inspect(Device("sw", "127.0.0.1", "", port, "u", "p"),
                         connect_timeout=2, command_timeout=3,
                         event_callback=lambda kind, **payload: events.append((kind, payload)))
    assert result.status == "ok", result.error
    assert result.pagination_mode == "automatic"
    assert "Console 不支持 VTY" in result.error
    assert "must be VTY" in result.outputs[PAGING["huawei"]]
    output = result.outputs["display current-configuration"]
    assert "sysname Huawei" in output and "interface Vlanif1" in output and "return" in output
    assert "More" not in output and "\x1b" not in output and "\b" not in output
    assert state["spaces"] == [b" ", b" "]
    assert state["commands"] == ["display version", PAGING["huawei"], *DEFAULT_COMMANDS["huawei"]]
    assert any(kind == "pagination_fallback" for kind, payload in events)


def test_successful_ssh_and_command_failure_never_trigger_telnet():
    class SSH:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def find_prompt(self): return "<SW>"
        def send_command(self, command, **kwargs):
            raise paramiko.SSHException("session lost")
    def never_telnet(*args):
        pytest.fail("command failure must not trigger Telnet")
    result = inspect(Device("sw", "192.0.2.1", "", 22, "u", "p"),
                     connector=lambda **kwargs: SSH(), telnet_connector=never_telnet)
    assert result.status == "fail"
    assert result.transport == "ssh"


def test_ssh_authentication_failure_falls_back_once():
    calls = []
    def ssh(**kwargs):
        calls.append("ssh")
        raise paramiko.AuthenticationException("test-password")
    def telnet(device, timeout):
        calls.append(("telnet", device.port))
        raise SafetyError("Telnet 认证失败")
    result = inspect(Device("sw", "192.0.2.1", "", 2000, "u", "test-password"),
                     connector=ssh, telnet_connector=telnet)
    assert calls == ["ssh", ("telnet", 2000)]
    assert "SSH 认证失败" in result.error and "Telnet 认证失败" in result.error
    assert "test-password" not in str(result)


def test_incremental_telnet_controls_and_escaped_iac():
    class Socket:
        def __init__(self): self.sent = []
        def sendall(self, value): self.sent.append(value)
    sock = Socket()
    channel = TelnetChannel(sock)
    for value in b"\xff\xfb\x01\xff\xfb\x01\xff\xfd\x18\xff\xfa\x18secret\xff\xf0data\xff\xff\r\x00":
        channel._feed(bytes([value]))
    assert channel.recv(1024) == b"data\xff\r"
    assert sock.sent == [b"\xff\xfd\x01", b"\xff\xfc\x18"]
    channel.send("display version\n")
    assert sock.sent[-1] == b"display version\r\n"


@pytest.mark.parametrize("console_paging", [False, True])
def test_fallback_events_and_transport_survive_backend_archive(tmp_path, console_paging):
    from backend import Api
    api = Api(tmp_path, collector=lambda device, **kwargs: inspect(
        device, connect_timeout=2, command_timeout=2, **kwargs))
    with telnet_device(console_paging=console_paging) as (port, state):
        asset = dict(name="sw", host="127.0.0.1", vendor="", port=port,
                     username="test-user", password="test-password", group="lab")
        assert api.save_asset(asset)["ok"]
        assert api.start_run(["127.0.0.1"], 1, commands=api.snapshot()["commands"], confirmed=True)["ok"]
        deadline = time.monotonic() + 8
        while api.snapshot()["run"]["state"] in ("running", "cancelling"):
            assert time.monotonic() < deadline
            time.sleep(.02)
    snap = api.snapshot()
    run = snap["run"]
    assert run["state"] == "done", run
    assert run["results"][0]["transport"] == "telnet"
    assert run["results"][0]["ssh_error"]
    assert run["results"][0]["pagination_mode"] == ("automatic" if console_paging else "disabled")
    if console_paging:
        assert any("Console 不支持 VTY" in log["message"] for log in run["logs"])
        configuration = (tmp_path / "reports" / run["id"] / "127.0.0.1_current-configuration.txt").read_text(encoding="utf-8")
        assert "sysname Huawei" in configuration and "return" in configuration
        assert "More" not in configuration
    assert "同端口 Telnet" in run["logs"][0]["message"]
    assert run["consoles"][0]["transport"] == "telnet"
    assert run["consoles"][0]["status"] == "done"
    assert "test-user" not in str(snap)
    assert "test-password" not in str(snap)
    for path in (tmp_path / "reports" / run["id"]).iterdir():
        text = path.read_text(encoding="utf-8")
        assert "test-user" not in text and "test-password" not in text
    assert "TELNET" in (tmp_path / "reports" / run["id"] / "report.html").read_text(encoding="utf-8")
    assert api.get_result("127.0.0.1")["transport"] == "telnet"
    assert Api(tmp_path).snapshot()["history"][0]["results"][0]["transport"] == "telnet"
