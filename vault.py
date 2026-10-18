"""Windows account-bound credential encryption. No plaintext fallback."""
import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def crypt(value: bytes, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("凭据保护需要 Windows")
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    library = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        fn = library.CryptUnprotectData
        fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        args = (ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target))
    else:
        fn = library.CryptProtectData
        fn.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        args = (ctypes.byref(source), "Switch Inspector credentials", None, None, None, 1,
                ctypes.byref(target))
    fn.restype = wintypes.BOOL
    if not fn(*args):
        raise RuntimeError("Windows 凭据加解密失败，请使用保存凭据的 Windows 账户")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


class Vault:
    def __init__(self, path):
        self.path = Path(path)
        self.assets, self.history = [], []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.history = data.get("history", [])
            for raw in data.get("assets", []):
                record = dict(raw)
                record.update(json.loads(crypt(base64.b64decode(record.pop("credentials")), True)))
                self.assets.append(record)

    def save(self):
        records = []
        for asset in self.assets:
            record = {k: v for k, v in asset.items() if k not in ("username", "password")}
            credentials = json.dumps({k: asset[k] for k in ("username", "password")}, ensure_ascii=False)
            record["credentials"] = base64.b64encode(crypt(credentials.encode())).decode()
            records.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps({"version": 2, "assets": records, "history": self.history},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)
