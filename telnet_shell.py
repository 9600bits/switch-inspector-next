"""Bounded Telnet login and interactive shell, without removed stdlib telnetlib."""
import re
import select
import socket
import time

from secure_collector import ParamikoShell, SafetyError


class TelnetChannel:
    """Socket adapter with incremental IAC parsing, including split negotiations."""
    def __init__(self, sock):
        self.sock = sock
        self.buffer = bytearray()
        self.state = "data"
        self.negotiation = None
        self.closed = False
        self.options = {}

    def _feed(self, data):
        for value in data:
            if self.state == "data":
                if value == 255:
                    self.state = "iac"
                elif value != 0:  # NVT CR NUL represents a bare CR.
                    self.buffer.append(value)
            elif self.state == "iac":
                if value == 255:
                    self.buffer.append(value)
                    self.state = "data"
                elif value in (251, 252, 253, 254):
                    self.negotiation = value
                    self.state = "option"
                elif value == 250:
                    self.state = "sub"
                else:
                    self.state = "data"
            elif self.state == "option":
                # Accept remote echo and suppress-go-ahead; refuse local echo,
                # terminal types and other options we do not implement.
                cmd = self.negotiation
                key = ("remote" if cmd in (251, 252) else "local", value)
                enabled = cmd in (251, 253)
                accepted = value in (1, 3) if cmd == 251 else value == 3
                if self.options.get(key) != enabled:
                    if cmd == 251:
                        self.sock.sendall(bytes((255, 253 if accepted else 254, value)))
                    elif cmd == 253:
                        self.sock.sendall(bytes((255, 251 if accepted else 252, value)))
                    self.options[key] = enabled
                self.state = "data"
            elif self.state == "sub":
                if value == 255:
                    self.state = "sub_iac"
            elif self.state == "sub_iac":
                self.state = "data" if value == 240 else "sub"

    def recv_ready(self):
        if self.buffer:
            return True
        if self.closed:
            raise SafetyError("Telnet 会话被设备关闭")
        if select.select([self.sock], [], [], 0)[0]:
            data = self.sock.recv(65536)
            if not data:
                self.closed = True
                raise SafetyError("Telnet 会话被设备关闭")
            self._feed(data)
        return bool(self.buffer)

    def recv(self, size):
        value = bytes(self.buffer[:size])
        del self.buffer[:size]
        return value

    def send(self, text):
        value = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
        self.sock.sendall(value.replace(b"\xff", b"\xff\xff"))

    def close(self):
        self.closed = True
        self.sock.close()


class TelnetShell(ParamikoShell):
    """Reuse the SSH collector's command/prompt/output boundaries after login."""
    def __init__(self, device, timeout):
        self.channel = None
        self.socket = None
        try:
            self.socket = socket.create_connection((device.host, device.port), timeout=timeout)
            self.socket.settimeout(1.0)
            self.channel = TelnetChannel(self.socket)
            self._prompt = self._login(device, timeout)
        except Exception as exc:
            self.close()
            if isinstance(exc, SafetyError):
                raise
            raise SafetyError("Telnet 连接或登录失败，请核对端口、账户及设备 Telnet 服务") from exc

    def _login(self, device, timeout):
        # Never stream authentication text or credential echoes into UI events.
        if any(any(c in value for c in "\r\n\x00") for value in (device.username, device.password)):
            raise SafetyError("Telnet 登录凭据不能包含换行或空字符")
        deadline = time.monotonic() + timeout
        pending = b""
        size = 0
        sent_user = sent_password = prompted = False
        last_data = time.monotonic()
        while time.monotonic() < deadline:
            if not self.channel.recv_ready():
                # Some console/Telnet servers show their prompt after Return.
                if not prompted and not pending and time.monotonic() - last_data > .5:
                    self.channel.send("\n")
                    prompted = True
                time.sleep(.02)
                continue
            chunk = self.channel.recv(65536)
            size += len(chunk)
            if size > 65536:
                raise SafetyError("Telnet 登录输出超过上限")
            pending += chunk
            last_data = time.monotonic()
            text = pending.decode("utf-8", "replace").replace("\r", "")
            text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
            if not prompted and re.search(r"press\s+(?:enter|return)|按.*回车", text, re.I):
                self.channel.send("\n")
                prompted = True
                pending = b""
                continue
            if re.search(r"(?:authentication failed|login (?:failed|incorrect)|access denied|invalid password|认证失败|密码错误)", text, re.I):
                raise SafetyError("Telnet 认证失败，请核对账户、密码及登录权限")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines and re.fullmatch(r"(?:<[^<>\r\n]{1,128}>|\[[^\[\]\r\n]{1,128}\])", lines[-1]):
                return lines[-1]
            if re.search(r"(?:username|user name|login|用户名)\s*[:：]\s*$", text, re.I):
                if sent_user or sent_password:
                    raise SafetyError("Telnet 认证失败，设备重新要求登录")
                self.channel.send(device.username + "\n")
                sent_user = True
                pending = b""
            elif re.search(r"(?:password|密码)\s*[:：]\s*$", text, re.I):
                if sent_password:
                    raise SafetyError("Telnet 认证失败，设备重新要求密码")
                self.channel.send(device.password + "\n")
                sent_password = True
                pending = b""
        raise SafetyError("Telnet 登录超时，未获得设备用户视图提示符")

    def close(self):
        if self.channel is not None:
            self.channel.close()
        elif self.socket is not None:
            self.socket.close()
