"""Real loopback TCP/SSH tests; no physical switch or external network required."""
from contextlib import contextmanager
import socket
import threading
import time
from unittest.mock import Mock

import paramiko
import pytest

import secure_collector
from devices import Device
from secure_collector import PAGING, SafetyError, _connect_ssh_socket, inspect


@contextmanager
def tcp_banner(parts):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(3)
    received = []
    errors = []

    def serve():
        try:
            with listener.accept()[0] as peer:
                peer.settimeout(3)
                for part in parts:
                    peer.sendall(part)
                    time.sleep(.02)
                try:
                    received.append(peer.recv(4096))
                except ConnectionResetError:
                    # Windows resets a socket closed with an unread peeked banner.
                    received.append(b"")
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1], received
    finally:
        thread.join(4)
        listener.close()
        assert not thread.is_alive()
        assert not errors, errors


@pytest.mark.parametrize("banner", [b"<Huawei>", b"\xff\xfb\x01", b"Username:", b"login:"])
def test_console_rejected_without_transmitting_ssh_or_credentials(banner):
    with tcp_banner([banner]) as (port, received):
        with pytest.raises(SafetyError, match="控制台/Telnet"):
            _connect_ssh_socket("127.0.0.1", port, 1)
    assert received == [b""]


@pytest.mark.parametrize("version", [b"2.0", b"1.99"])
def test_partial_ssh_banner_and_preamble_remain_unread_for_paramiko(version):
    banner = b"Authorized access only\r\nSSH-" + version + b"-TestServer\r\n"
    with tcp_banner([banner[:8], banner[8:]]) as (port, received):
        with _connect_ssh_socket("127.0.0.1", port, 1) as peer:
            assert peer.recv(8192) == banner
    assert received == [b""]


def test_silent_console_times_out_without_sending_client_data():
    with tcp_banner([]) as (port, received):
        with pytest.raises(SafetyError, match="超时内返回 SSH2"):
            _connect_ssh_socket("127.0.0.1", port, .1)
    assert received == [b""]


def test_ssh1_rejected_without_sending_client_data():
    with tcp_banner([b"SSH-1.5-OldServer\r\n"]) as (port, received):
        with pytest.raises(SafetyError, match="SSH1"):
            _connect_ssh_socket("127.0.0.1", port, 1)
    assert received == [b""]


@pytest.mark.parametrize("error, expected", [
    (paramiko.AuthenticationException("secret-user secret-password"), "认证失败"),
    (paramiko.ssh_exception.IncompatiblePeer("no acceptable kex algorithm secret-password"), "密钥交换算法不兼容"),
    (paramiko.ssh_exception.IncompatiblePeer("no acceptable host key"), "主机密钥算法不兼容"),
    (paramiko.SSHException("Error reading SSH protocol banner secret-password"), "协议标识读取失败"),
    (paramiko.ChannelException(1, "secret-password"), "终端通道被拒绝"),
    (paramiko.SSHException("PTY request failed secret-password"), "终端分配请求"),
    (ConnectionRefusedError("secret-user secret-password"), "无法建立 TCP 连接"),
])
def test_errors_and_realtime_events_are_actionable_without_credentials(error, expected):
    events = []
    def failed_connector(**kwargs):
        raise error
    result = inspect(Device("sw", "127.0.0.1", "", 22, "secret-user", "secret-password"),
                     connector=failed_connector,
                     event_callback=lambda kind, **payload: events.append((kind, payload)))
    assert result.status == "fail"
    assert expected in result.error
    assert events[-1] == ("device_error", {"host": "127.0.0.1", "error": result.error})
    assert "secret-user" not in str(events) + result.error
    assert "secret-password" not in str(events) + result.error


def test_handshake_failure_reports_stage_and_closes_resources(monkeypatch):
    sock = Mock()
    client = Mock()
    client.connect.side_effect = paramiko.ssh_exception.IncompatiblePeer("no acceptable kex algorithm")
    monkeypatch.setattr(secure_collector, "_connect_ssh_socket", lambda *args: sock)
    monkeypatch.setattr(paramiko, "SSHClient", lambda: client)
    def no_telnet(device, timeout):
        raise SafetyError("Telnet 服务不可用")
    result = inspect(Device("sw", "127.0.0.1", "", 22, "user", "password"), telnet_connector=no_telnet)
    assert "SSH 握手与认证失败" in result.error
    assert "密钥交换算法不兼容" in result.error
    assert client.connect.call_args.kwargs["sock"] is sock
    client.invoke_shell.assert_not_called()
    client.close.assert_called_once()
    sock.close.assert_called_once()


class SwitchServer(paramiko.ServerInterface):
    def __init__(self):
        self.shell_ready = threading.Event()

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL if (username, password) == ("test-user", "test-password") else paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, *args):
        return True

    def check_channel_shell_request(self, channel):
        self.shell_ready.set()
        return True


@pytest.mark.parametrize("vendor, version", [
    ("huawei", "Huawei Versatile Routing Platform Version 8.200"),
    ("hp_comware", "H3C Comware Software, Version 7.1.070\nH3C S5130 uptime is 1 day"),
])
def test_real_password_ssh_shell_and_collection_order(vendor, version):
    key = paramiko.RSAKey.generate(2048)
    commands = []
    errors = []
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(8)
    port = listener.getsockname()[1]

    def serve():
        try:
            with listener.accept()[0] as peer, paramiko.Transport(peer) as transport:
                transport.add_server_key(key)
                server = SwitchServer()
                transport.start_server(server=server)
                channel = transport.accept(5)
                assert channel is not None
                assert server.shell_ready.wait(5)
                channel.settimeout(5)
                channel.sendall(b"<Switch>")
                pending = b""
                while True:
                    block = channel.recv(4096)
                    if not block:
                        break
                    pending += block
                    while b"\n" in pending:
                        command, pending = pending.split(b"\n", 1)
                        command = command.decode().strip()
                        commands.append(command)
                        output = version if command == "display version" else "test output"
                        channel.sendall((command + "\r\n" + output + "\r\n<Switch>").encode())
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        result = inspect(Device("local-test", "127.0.0.1", "", port, "test-user", "test-password"),
                         connect_timeout=3, command_timeout=3,
                         command_sets={vendor: ["display device"]})
    finally:
        thread.join(8)
        listener.close()
    assert not thread.is_alive()
    assert not errors, errors
    assert result.status == "ok", result.error
    assert result.transport == "ssh"
    assert result.detected_vendor == vendor
    assert commands == ["display version", PAGING[vendor], "display device"]
    assert result.outputs["display device"] == "test output"
