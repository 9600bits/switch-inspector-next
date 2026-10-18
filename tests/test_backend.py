"""Offline tests of the new desktop path. Never connect to a real device."""
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import Api
from secure_collector import Collection, inspect, PAGING, COMMANDS, ParamikoShell, SafetyError
from devices import Device
from vault import Vault


def asset(host="192.0.2.1"):
    return dict(name="<script>alert(1)</script>", host=host, vendor="huawei", port=22,
                username="login-user-unique", password="password-unique-123", group="实验室")


def result(device):
    return Collection(device.host, device.vendor, outputs={
        "display cpu-usage": "CPU usage: 12%", "display memory-usage": "Memory usage: 36%",
        "display device": "FAN1 Present FAN Normal\nPWR1 Present POWER Normal",
        "display current-configuration": "<script>unsafe</script>\n" + device.username + " " + device.password})


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.api = Api(self.temp.name, collector=result)

    def tearDown(self):
        self.temp.cleanup()

    def finish(self):
        deadline = time.monotonic() + 5
        while self.api._run["state"] in ("running", "cancelling"):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.02)

    def test_encrypted_credentials_and_public_snapshot(self):
        record = asset()
        self.assertTrue(self.api.save_asset(record)["ok"])
        source = self.api._store.path.read_text(encoding="utf-8")
        self.assertNotIn(record["password"], source)
        self.assertNotIn(record["username"], source)
        self.assertEqual(Vault(self.api._store.path).assets[0]["password"], record["password"])
        self.assertNotIn(record["username"], json.dumps(self.api.snapshot()))
        self.assertNotIn(record["password"], json.dumps(self.api.snapshot()))
        self.assertIn("error", self.api.save_asset(record))
        record["password"] = record["username"] = ""
        self.assertTrue(self.api.save_asset(record, record["host"])["ok"])
        self.assertEqual(self.api._store.assets[0]["password"], asset()["password"])

    def test_archive_escaping_redaction_metrics_and_reopen(self):
        self.api.save_asset(asset())
        self.assertTrue(self.api.start_run(["192.0.2.1"], 2)["ok"])
        self.finish()
        self.assertEqual(self.api._run["state"], "done")
        row = self.api.get_result("192.0.2.1")
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["metrics"]["cpu"], 12)
        folder = Path(self.temp.name) / "reports" / self.api._run["id"]
        for path in folder.iterdir():
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(asset()["password"], text)
            self.assertNotIn(asset()["username"], text)
        report = (folder / "report.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertTrue((folder / "192.0.2.1_current-configuration.txt").exists())
        restarted = Api(self.temp.name)
        self.assertEqual(restarted.snapshot()["assets"][0]["result"]["status"], "ok")
        self.assertIn("display current-configuration", restarted.get_result("192.0.2.1")["outputs"])
        self.assertNotIn("outputs", self.api.snapshot()["run"]["results"][0])

    def test_cidr_duplicate_limit_and_validation(self):
        record = dict(asset(), cidr="192.0.2.0/30")
        self.assertEqual(self.api.add_cidr(record)["added"], 2)
        self.assertEqual(self.api.add_cidr(record)["skipped"], 2)
        self.assertEqual(self.api.add_cidr(dict(record, cidr="192.0.2.4/31"))["added"], 2)
        self.assertIn("error", self.api.add_cidr(dict(record, cidr="10.0.0.0/8")))
        self.assertIn("error", self.api.add_cidr(dict(record, cidr="::1/128")))
        self.assertIn("error", self.api.start_run([], 0))

    def test_h3c_ui_vendor_and_edit_roundtrip(self):
        record = dict(asset(), vendor="hp_comware")
        self.assertTrue(self.api.save_asset(record)["ok"])
        self.assertTrue(self.api.save_asset(dict(record, password="", username=""), record["host"])["ok"])
        self.assertEqual(self.api.snapshot()["assets"][0]["vendor"], "hp_comware")

    def test_vendor_can_be_left_unspecified_until_inspection(self):
        record = dict(asset(), vendor="")
        self.assertTrue(self.api.save_asset(record)["ok"])
        self.assertEqual(self.api.snapshot()["assets"][0]["vendor"], "")
        response = self.api.start_run([record["host"]], 1)
        self.assertTrue(response["ok"])
        self.finish()
        self.assertEqual(self.api._run["state"], "done")

    def test_cancel_stops_dispatch_and_rejects_reentry(self):
        entered, release = threading.Event(), threading.Event()
        called = []
        def blocked(device):
            called.append(device.host)
            entered.set()
            release.wait(4)
            return result(device)
        self.api._collector = blocked
        for i in range(1, 5):
            self.api.save_asset(asset(f"192.0.2.{i}"))
        hosts = [a["host"] for a in self.api._store.assets]
        self.api.start_run(hosts, 1)
        self.assertTrue(entered.wait(2))
        try:
            self.assertIn("error", self.api.start_run(hosts, 1))
            self.assertIn("error", self.api.delete_assets(hosts))
            self.api.cancel_run()
        finally:
            release.set()
        self.finish()
        self.assertEqual(len(called), 1)
        self.assertEqual(self.api._run["state"], "cancelled")
        self.assertEqual(self.api.snapshot()["history"][0]["count"], 1)

    def test_unparsed_metrics_are_unknown(self):
        self.api._collector = lambda d: Collection(d.host, d.vendor, outputs={"display cpu-usage": "unsupported"})
        self.api.save_asset(asset())
        self.api.start_run(["192.0.2.1"], 1)
        self.finish()
        self.assertEqual(self.api._run["results"][0]["status"], "unknown")


class CollectorBoundaryTests(unittest.TestCase):
    def test_pagination_stops_following_commands(self):
        class Fake:
            def __init__(self): self.commands = []
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def find_prompt(self): return "<TEST>"
            def send_command(self, command, **kwargs):
                self.commands.append(command)
                return "---- More ----" if command.startswith("display") else ""
        conn = Fake()
        value = inspect(Device(**asset()), connector=lambda **kwargs: conn)
        self.assertEqual(value.status, "fail")
        self.assertEqual(conn.commands, ["display version"])

    def test_configuration_prompt_does_not_reuse_old_user_prompt(self):
        shell = object.__new__(ParamikoShell)
        shell._prompt = "<TEST>"
        shell.channel = type("Channel", (), {"send": lambda self, value: None})()
        shell._read_until_quiet = lambda timeout: "display cpu-usage\nCPU usage: 10%\n[TEST]\n\n"
        with self.assertRaises(SafetyError):
            shell.send_command("display cpu-usage")

    def test_slow_output_waits_for_prompt_and_missing_prompt_fails(self):
        shell = object.__new__(ParamikoShell)
        shell.channel = type("Channel", (), {"recv_ready": lambda self: False})()
        with self.assertRaises(SafetyError):
            shell._read_until_quiet(.02)


if __name__ == "__main__":
    unittest.main(verbosity=2)
