"""Desktop bridge: assets, bounded scheduling and escaped, credential-free reports."""
import copy
import sys
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime
from pathlib import Path

from assets import normalize, expand_cidr, expand_range, import_xlsx, write_template, AssetError
from devices import Device
from secure_collector import inspect, DEFAULT_COMMANDS, ANALYSIS_COMMANDS, normalize_commands
from reporting import analyze_device, build_report, render_body, render_document
from vault import Vault
import parsers

MAX_WORKERS = 16
CONSOLE_BUFFER_LIMIT = 120_000


def public(asset):
    return {k: v for k, v in asset.items() if k not in ("password", "username", "credentials")}


def metrics(vendor, outputs):
    if vendor not in ("huawei", "hp_comware"):
        return {}
    keys = ({"cpu": "display cpu-usage", "memory": "display memory-usage", "fanpower": "display device"}
            if vendor == "huawei" else
            {"cpu": "display cpu-usage summary", "memory": "display memory", "fan": "display fan", "power": "display power"})
    values = {}
    for key, command in keys.items():
        try:
            value = parsers.parse(vendor, key, outputs.get(command, ""))
            values[key] = value["pct"] if key in ("cpu", "memory") else value
        except (ValueError, KeyError):
            values[key] = None
    return values


def health(values, failed=False):
    if failed:
        return "fail"
    if any(values.get(key) is not None and values[key] >= 80 for key in ("cpu", "memory")):
        return "warn"
    for key in ("fanpower", "fan", "power"):
        value = values.get(key) or {}
        if any(str(unit.get("state", "")).lower() in ("abnormal", "fault", "off", "absent", "invalid", "notpresent")
               for unit in value.get("units", [])):
            return "warn"
    hardware = [values.get(key) for key in ("fanpower", "fan", "power") if key in values]
    if any(values.get(key) is None for key in ("cpu", "memory")) or any(not v or not v.get("found") for v in hardware):
        return "unknown"
    return "ok"


class Api:
    def __init__(self, base=None, collector=inspect):
        self._base = Path(base or Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SwitchInspectorNext")
        self._store = Vault(self._base / "data" / "assets.json")
        self._commands_path = self._base / "data" / "commands.json"
        self._commands = self._load_commands()
        self._lock = threading.RLock()
        self._cancel_event = threading.Event()
        self._collector = collector
        self._window = None
        self._run = {"state": "idle", "total": 0, "completed": 0, "results": [], "logs": [], "active": []}

    def _load_commands(self):
        value = copy.deepcopy(DEFAULT_COMMANDS)
        try:
            raw = json.loads(self._commands_path.read_text(encoding="utf-8"))
            for vendor in value:
                if vendor in raw:
                    value[vendor] = normalize_commands(raw[vendor])
        except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError):
            pass
        return {vendor: normalize_commands(rows) for vendor, rows in value.items()}

    def _save_commands(self):
        self._commands_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._commands_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self._commands, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self._commands_path)

    def snapshot(self):
        with self._lock:
            latest = {}
            for item in self._store.history:
                for row in item.get("results", []):
                    latest[row["host"]] = row
            for row in self._run["results"]:
                latest[row["host"]] = {k: v for k, v in row.items() if k != "outputs"}
            run = {k: copy.deepcopy(v) for k, v in self._run.items() if k != "results"}
            run["results"] = [{k: copy.deepcopy(v) for k, v in row.items() if k != "outputs"} for row in self._run["results"]]
            return {"assets": [dict(public(a), result=latest.get(a["host"])) for a in self._store.assets],
                    "history": copy.deepcopy(self._store.history[-100:][::-1]),
                    "run": run, "commands": copy.deepcopy(self._commands),
                    "analysis_commands": copy.deepcopy(ANALYSIS_COMMANDS), "data_dir": str(self._base)}

    def save_commands(self, vendor, commands):
        if vendor not in DEFAULT_COMMANDS:
            return {"error": "不支持的设备平台"}
        try:
            rows = normalize_commands(commands)
        except (ValueError, TypeError, AttributeError) as exc:
            return {"error": str(exc)}
        with self._lock:
            self._commands[vendor] = rows
            self._save_commands()
        return {"ok": True, "commands": copy.deepcopy(rows)}

    def reset_commands(self, vendor):
        if vendor not in DEFAULT_COMMANDS:
            return {"error": "不支持的设备平台"}
        with self._lock:
            self._commands[vendor] = normalize_commands(DEFAULT_COMMANDS[vendor])
            self._save_commands()
        return {"ok": True, "commands": copy.deepcopy(self._commands[vendor])}

    def save_asset(self, record, original_host=None):
        try:
            with self._lock:
                if self._run["state"] in ("running", "cancelling"):
                    raise AssetError("请等待当前巡检结束后修改资产")
                existing = next((a for a in self._store.assets if a["host"] == original_host), None)
                clean = {k: record.get(k, "") for k in ("name", "host", "vendor", "port", "group", "username", "password")}
                for key in ("detected_vendor", "model", "version", "uptime", "serial_number"):
                    clean[key] = record.get(key, existing.get(key, "") if existing else "")
                if existing:
                    for key in ("username", "password"):
                        if not clean[key]:
                            clean[key] = existing[key]
                clean = normalize(clean)
                if any(a["host"] == clean["host"] and a["host"] != original_host for a in self._store.assets):
                    raise AssetError("该 IP 已存在，请编辑已有设备")
                self._store.assets = [clean if a["host"] == original_host else a for a in self._store.assets]
                if not existing:
                    self._store.assets.append(clean)
                self._store.save()
            return {"ok": True}
        except AssetError as exc:
            return {"error": str(exc)}

    def delete_assets(self, hosts):
        with self._lock:
            if self._run["state"] in ("running", "cancelling"):
                return {"error": "巡检进行中，暂不能删除设备"}
            self._store.assets = [a for a in self._store.assets if a["host"] not in hosts]
            self._store.save()
        return {"ok": True}

    def add_cidr(self, record):
        try:
            addresses = expand_cidr(record.get("cidr", ""))
            items = [normalize(dict(record, host=ip, name=ip)) for ip in addresses]
            return self._merge(items)
        except AssetError as exc:
            return {"error": str(exc)}

    def add_range(self, record):
        try:
            addresses = expand_range(record.get("range", ""))
            return self._merge([normalize(dict(record, host=ip, name=ip)) for ip in addresses])
        except AssetError as exc:
            return {"error": str(exc)}

    def _merge(self, items):
        with self._lock:
            if self._run["state"] in ("running", "cancelling"):
                return {"error": "巡检进行中，暂不能导入设备"}
            existing = {a["host"] for a in self._store.assets}
            added = 0
            for item in items:
                if item["host"] not in existing:
                    self._store.assets.append({k: item[k] for k in ("name", "host", "vendor", "port", "group", "username", "password")})
                    existing.add(item["host"])
                    added += 1
            self._store.save()
            return {"ok": True, "added": added, "skipped": len(items) - added}

    def import_excel(self):
        import webview
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, file_types=("Excel (*.xlsx)",))
        if not paths:
            return {"cancelled": True}
        try:
            return self._merge(import_xlsx(paths[0]))
        except AssetError as exc:
            return {"error": str(exc)}
        except Exception:
            return {"error": "无法读取此 Excel 文件，请确认格式并关闭文件后重试"}

    def save_template(self):
        import webview
        path = self._window.create_file_dialog(webview.FileDialog.SAVE, save_filename="交换机资产模板.xlsx", file_types=("Excel (*.xlsx)",))
        if not path:
            return {"cancelled": True}
        if isinstance(path, (list, tuple)):
            path = path[0]
        target = Path(path).with_suffix(".xlsx")
        write_template(target)
        return {"ok": True}

    def start_run(self, hosts, workers=5, commands=None, collect_sn=False, confirmed=False):
        try:
            workers = int(workers)
        except (ValueError, TypeError):
            return {"error": "并发数必须为 1–16 的整数"}
        if not 1 <= workers <= MAX_WORKERS:
            return {"error": "并发数必须为 1–16 的整数"}
        with self._lock:
            if self._run["state"] in ("running", "cancelling"):
                return {"error": "已有巡检正在运行"}
            assets = copy.deepcopy([a for a in self._store.assets if a["host"] in hosts])
            if not assets:
                return {"error": "请先选择需要巡检的设备"}
            if commands is not None and not confirmed:
                return {"error": "请先人工确认本次巡检命令"}
            command_sets = copy.deepcopy(commands) if commands is not None else copy.deepcopy(self._commands)
            try:
                command_sets = {vendor: normalize_commands(rows) for vendor, rows in command_sets.items()}
            except (ValueError, AttributeError, TypeError) as exc:
                return {"error": f"命令清单无效：{exc}"}
            self._cancel_event.clear()
            consoles = [{"slot": index + 1, "host": "", "name": "", "command": "", "status": "idle",
                         "output": "", "started": "", "updated": "", "finished": "", "error": ""}
                        for index in range(min(workers, len(assets)))]
            self._run = {"state": "running", "total": len(assets), "completed": 0, "results": [],
                        "logs": [], "active": [], "started": datetime.now().isoformat(),
                        "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"), "workers": workers,
                        "collect_sn": bool(collect_sn), "consoles": consoles}
            threading.Thread(target=self._collect, args=(assets, workers, command_sets, bool(collect_sn)), daemon=True).start()
        return {"ok": True}

    def cancel_run(self):
        with self._lock:
            if self._run["state"] == "running":
                self._cancel_event.set()
                self._run["state"] = "cancelling"
        return {"ok": True}

    def _collect(self, assets, workers, command_sets=None, collect_sn=False):
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                pending, todo = {}, iter(assets)

                def console_event(slot, asset, kind, **payload):
                    with self._lock:
                        consoles = self._run.get("consoles", [])
                        if slot >= len(consoles):
                            return
                        console = consoles[slot]
                        now = datetime.now().isoformat()
                        def scrub(value):
                            text = str(value or "")
                            for secret in (asset.get("password", ""), asset.get("username", "")):
                                if secret:
                                    text = text.replace(secret, "[REDACTED]")
                            return text
                        console["updated"] = now
                        if kind == "device_start":
                            console.update({"host": asset["host"], "name": asset.get("name", ""), "command": "",
                                            "status": "connecting", "output": "", "started": now,
                                            "finished": "", "error": ""})
                            console["transport"] = payload.get("transport", "ssh")
                        elif kind == "connection_fallback":
                            message = scrub(payload.get("message", "SSH 登录失败，正在尝试 Telnet"))
                            console.update({"status": "connecting", "transport": "telnet", "output": message})
                            self._run["logs"].append({"time": datetime.now().strftime("%H:%M:%S"),
                                "host": asset["host"], "status": "running", "message": message})
                        elif kind == "pagination_fallback":
                            self._run["logs"].append({"time": datetime.now().strftime("%H:%M:%S"),
                                "host": asset["host"], "status": "running", "message": scrub(payload.get("message", ""))})
                        elif kind == "command_start":
                            console.update({"command": payload.get("command", ""), "status": "running",
                                            "output": "", "error": ""})
                        elif kind == "output":
                            chunk = scrub(payload.get("chunk", ""))
                            console["output"] = (console.get("output", "") + chunk)[-CONSOLE_BUFFER_LIMIT:]
                        elif kind == "command_complete":
                            console["status"] = "complete"
                        elif kind == "command_error":
                            console.update({"status": "fail", "error": scrub(payload.get("error", ""))[-1000:]})
                        elif kind == "device_complete":
                            console.update({"status": "done", "finished": now})
                        elif kind == "device_error":
                            console.update({"status": "fail", "finished": now,
                                            "error": scrub(payload.get("error", ""))[-1000:]})

                def invoke(asset, slot):
                    device = Device(**{k: asset[k] for k in ("name", "host", "vendor", "port", "username", "password", "group")})
                    callback = lambda kind, **payload: console_event(slot, asset, kind, **payload)
                    try:
                        return self._collector(device, command_sets=command_sets, collect_sn=collect_sn,
                                               event_callback=callback)
                    except TypeError as exc:
                        if "event_callback" not in str(exc) and "unexpected keyword" not in str(exc):
                            raise
                        try:
                            return self._collector(device, command_sets=command_sets, collect_sn=collect_sn)
                        except TypeError as retry_exc:
                            if "unexpected keyword" not in str(retry_exc) and "positional argument" not in str(retry_exc):
                                raise
                            return self._collector(device)

                def submit(slot):
                    with self._lock:
                        if self._cancel_event.is_set():
                            return
                        asset = next(todo, None)
                        if asset:
                            now = datetime.now().isoformat()
                            self._run["consoles"][slot].update({"host": asset["host"], "name": asset.get("name", ""),
                                "command": "", "status": "queued", "output": "", "started": now,
                                "updated": now, "finished": "", "error": "", "transport": ""})
                            pending[pool.submit(invoke, asset, slot)] = (asset, slot)
                            self._run["active"].append(asset["host"])

                for slot in range(min(workers, len(assets))):
                    submit(slot)
                while pending:
                    completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in completed:
                        asset, slot = pending.pop(future)
                        result = None
                        try:
                            result = future.result()
                            outputs, error, failed = result.outputs, result.error, result.status == "fail"
                        except Exception:
                            outputs, error, failed = {}, "采集异常，请检查设备连接", True
                            with self._lock:
                                if slot < len(self._run.get("consoles", [])):
                                    self._run["consoles"][slot].update({"status": "fail", "finished": datetime.now().isoformat(),
                                                                         "updated": datetime.now().isoformat(), "error": error})
                        # Never expose an actual configured credential via output or errors.
                        ssh_error = getattr(result, "ssh_error", "")
                        for secret in (asset["password"], asset["username"]):
                            if secret:
                                outputs = {key: value.replace(secret, "[REDACTED]") for key, value in outputs.items()}
                                error = error.replace(secret, "[REDACTED]")
                                ssh_error = ssh_error.replace(secret, "[REDACTED]")
                        actual_vendor = getattr(result, "detected_vendor", "") or getattr(result, "vendor", "") or asset.get("vendor", "")
                        values = metrics(actual_vendor, outputs)
                        row = dict(public(asset), vendor=actual_vendor or asset.get("vendor", ""),
                                   detected_vendor=actual_vendor, model=getattr(result, "model", ""),
                                   version=getattr(result, "version", ""), uptime=getattr(result, "uptime", ""),
                                   serial_number=getattr(result, "serial_number", ""), metrics=values, status=health(values, failed),
                                   transport=getattr(result, "transport", ""), ssh_error=ssh_error,
                                   pagination_mode=getattr(result, "pagination_mode", ""),
                                   error=error, outputs=outputs, collected=datetime.now().isoformat(),
                                   requested_commands=getattr(result, "requested_commands", []) or list(outputs),
                                   command_status=getattr(result, "command_status", {}))
                        row["analysis"] = analyze_device(row)
                        row["status"] = row["analysis"]["status"]
                        if failed:
                            with self._lock:
                                if slot < len(self._run.get("consoles", [])):
                                    self._run["consoles"][slot].update({"status": "fail", "finished": datetime.now().isoformat(),
                                                                         "updated": datetime.now().isoformat(), "error": error or "采集失败"})
                        for key in ("vendor", "detected_vendor", "model", "version", "uptime", "serial_number"):
                            if row.get(key): asset[key] = row[key]
                        with self._lock:
                            for stored in self._store.assets:
                                if stored.get("host") == asset.get("host"):
                                    stored.update({key: asset[key] for key in ("vendor", "detected_vendor", "model", "version", "uptime", "serial_number") if key in asset})
                                    break
                            self._run["results"].append(row)
                            self._run["completed"] += 1
                            if asset["host"] in self._run["active"]:
                                self._run["active"].remove(asset["host"])
                            self._run["logs"].append({"time": datetime.now().strftime("%H:%M:%S"),
                                                      "host": asset["host"], "status": row["status"], "message": error or "状态与配置采集完成"})
                        submit(slot)
            self._archive()
        except Exception:
            with self._lock:
                self._run["state"] = "error"
                self._run["active"] = []
                self._run["error"] = "报告保存失败，请检查本地磁盘空间与写入权限"

    def _archive(self):
        with self._lock:
            run = copy.deepcopy(self._run)
        folder = self._base / "reports" / run["id"]
        folder.mkdir(parents=True, exist_ok=True)
        rows = run["results"]
        (folder / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        for row in rows:
            configuration = row["outputs"].get("display current-configuration")
            if configuration is not None:
                (folder / f'{row["host"]}_current-configuration.txt').write_text(configuration, encoding="utf-8")
        state = "cancelled" if self._cancel_event.is_set() else "done"
        report = build_report(dict(run, state=state), rows)
        resources = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "ui"
        (folder / "report.html").write_text(render_document(report, rows, resources), encoding="utf-8")
        item = {"id": run["id"], "started": run["started"], "state": state, "count": len(rows), "total": run["total"],
                "ok": sum(row["status"] == "ok" for row in rows), "warn": sum(row["status"] in ("warn", "unknown") for row in rows),
                "fail": sum(row["status"] == "fail" for row in rows),
                "results": [{k: v for k, v in row.items() if k != "outputs"} for row in rows]}
        with self._lock:
            self._store.history.append(item)
            self._store.save()
            self._run["state"] = state
            self._run["finished"] = datetime.now().isoformat()

    def get_report(self, run_id):
        with self._lock:
            item = next((copy.deepcopy(item) for item in self._store.history if item["id"] == run_id), None)
        if not item:
            return {"error": "报告不存在"}
        try:
            path = self._base / "reports" / item["id"] / "results.json"
            rows = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            # Old history summaries can still be read when the raw archive was moved.
            rows = item.get("results", [])
        except (OSError, ValueError):
            return {"error": "归档不可读取"}
        report = build_report(item, rows)
        report["html"] = render_body(report)
        return report

    def open_report(self, run_id, folder=False):
        with self._lock:
            if not any(item["id"] == run_id for item in self._store.history):
                return {"error": "报告不存在"}
        target = self._base / "reports" / run_id
        target = target if folder else target / "report.html"
        if not target.exists():
            return {"error": "归档文件不存在或已被移动"}
        os.startfile(str(target))
        return {"ok": True}

    def get_result(self, host, run_id=None):
        with self._lock:
            if not run_id:
                result = next((row for row in self._run["results"] if row["host"] == host), None)
                if result:
                    return copy.deepcopy(result)
                item = next((item for item in reversed(self._store.history) if any(row["host"] == host for row in item.get("results", []))), None)
            else:
                item = next((item for item in self._store.history if item["id"] == run_id), None)
        if item:
            try:
                rows = json.loads((self._base / "reports" / item["id"] / "results.json").read_text(encoding="utf-8"))
                return next((row for row in rows if row["host"] == host), {"error": "没有采集结果"})
            except (OSError, ValueError):
                return {"error": "归档不可读取"}
        return {"error": "此设备尚未巡检"}
