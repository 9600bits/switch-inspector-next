import tempfile
import time
import unittest

from backend import Api
from devices import Device
from secure_collector import inspect, validate_command, SafetyError, Collection


class FakeConnection:
    def __init__(self, version):
        self.version = version
        self.commands = []

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def find_prompt(self): return "<SW1>"

    def send_command(self, command, **kwargs):
        self.commands.append(command)
        if command == "display version":
            return self.version
        if command == "display device esn":
            return "ESN: SN-ABC1234"
        return "ok"


class CommandFeatureTests(unittest.TestCase):
    def test_command_events_and_console_slots(self):
        events = []
        conn = FakeConnection("Huawei Versatile Routing Platform")
        result = inspect(Device("sw", "192.0.2.9", "", 22, "u", "p"),
                         connector=lambda **kwargs: conn,
                         command_sets={"huawei": [{"command": "display version", "enabled": True}]},
                         event_callback=lambda kind, **payload: events.append(kind))
        self.assertEqual(result.status, "ok")
        self.assertEqual(events[0], "device_start")
        self.assertIn("command_start", events)
        self.assertIn("output", events)
        self.assertEqual(events[-1], "device_complete")

    def test_worker_limit_and_realtime_snapshot(self):
        def collector(device, event_callback=None, **kwargs):
            event_callback("device_start")
            event_callback("command_start", command="display version")
            event_callback("output", chunk="safe output")
            event_callback("command_complete", command="display version")
            event_callback("device_complete", status="ok")
            return Collection(device.host, "huawei")

        with tempfile.TemporaryDirectory() as folder:
            api = Api(folder, collector=collector)
            record = {"name": "sw", "host": "192.0.2.9", "vendor": "", "port": 22,
                      "username": "operator", "password": "s3cret", "group": "lab"}
            api.save_asset(record)
            self.assertIn("error", api.start_run([record["host"]], 17))
            self.assertTrue(api.start_run([record["host"]], 1)["ok"])
            deadline = time.monotonic() + 2
            while api._run["state"] in ("running", "cancelling") and time.monotonic() < deadline:
                time.sleep(.01)
            console = api.snapshot()["run"]["consoles"][0]
            self.assertEqual(console["status"], "done")
            self.assertEqual(console["output"], "safe output")
    def test_custom_show_command_and_platform_detection(self):
        conn = FakeConnection("Huawei Versatile Routing Platform\nVersion 8.200\nHUAWEI S5735 uptime is 1 day")
        result = inspect(Device("sw", "192.0.2.1", "hp_comware", 22, "u", "p"),
                         connector=lambda **kwargs: conn,
                         command_sets={"huawei": [{"command": "show interface brief", "enabled": True}]},
                         collect_sn=True)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.detected_vendor, "huawei")
        self.assertEqual(result.serial_number, "SN-ABC1234")
        self.assertEqual(conn.commands, ["display version", "screen-length 0 temporary", "show interface brief", "display device esn"])

    def test_unknown_platform_skips_collection_commands(self):
        conn = FakeConnection("vendor firmware 1.0")
        result = inspect(Device("sw", "192.0.2.1", "huawei", 22, "u", "p"), connector=lambda **kwargs: conn)
        self.assertEqual(result.status, "fail")
        self.assertEqual(conn.commands, ["display version"])

    def test_command_validation(self):
        self.assertEqual(validate_command(" show version "), "show version")
        for value in ("display version\nshow version", "display version; reboot", "reboot", ""):
            with self.assertRaises(ValueError):
                validate_command(value)

    def test_command_persistence_and_vendor_optional(self):
        with tempfile.TemporaryDirectory() as folder:
            api = Api(folder, collector=lambda device, **kwargs: None)
            self.assertTrue(api.save_commands("huawei", [{"command": "show version", "enabled": True}])["ok"])
            self.assertEqual(Api(folder).snapshot()["commands"]["huawei"][0]["command"], "show version")
            self.assertTrue(api.save_asset({"name": "sw", "host": "192.0.2.1", "vendor": "", "port": 22,
                                            "username": "operator", "password": "s3cret", "group": "lab"})["ok"])
            self.assertTrue(api.start_run(["192.0.2.1"], 1, commands=api.snapshot()["commands"], confirmed=True)["ok"])
            deadline = time.monotonic() + 2
            while api._run["state"] in ("running", "cancelling") and time.monotonic() < deadline:
                time.sleep(.01)


if __name__ == "__main__":
    unittest.main()

