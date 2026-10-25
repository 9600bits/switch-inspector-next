"""Deterministic inspection analysis and offline report rendering for the desktop API."""
import copy
import html
import math
from datetime import datetime
from pathlib import Path

import parsers
import rules
from secure_collector import CLI_ERROR

LABELS = {"ok": "正常", "warn": "需关注", "unknown": "待核实", "fail": "采集失败"}
ITEMS = {"cpu": "CPU", "memory": "内存", "temp": "温度", "fanpower": "风扇/电源",
         "alarm": "当前告警", "log": "最近日志", "ports": "端口", "errors": "累计错包"}
REASONS = {"not_collected": "未采集", "unsupported": "设备不支持", "unrecognized": "未识别"}


def command_map(vendor):
    return {"cpu": ["display cpu-usage" if vendor == "huawei" else "display cpu-usage summary"],
            "memory": ["display memory-usage" if vendor == "huawei" else "display memory"],
            "temp": ["display environment"],
            "fanpower": ["display device"] if vendor == "huawei" else ["display fan", "display power"],
            "alarm": ["display alarm active" if vendor == "huawei" else "display alarm"],
            "log": ["display logbuffer" if vendor == "huawei" else "display logbuffer reverse"],
            "ports": ["display interface brief"],
            "errors": ["display counters errors inbound", "display counters errors outbound"]}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def analyze_device(row):
    """Prefer stored analysis, then outputs, then older structured metrics."""
    if isinstance(row.get("analysis"), dict) and row["analysis"].get("schema") == 1:
        return copy.deepcopy(row["analysis"])
    vendor = row.get("detected_vendor") or row.get("vendor")
    canonical = lambda command: " ".join(command.lower().split())
    outputs = {canonical(k): v for k, v in (row.get("outputs") or {}).items()}
    requested = {canonical(cmd) for cmd in (row.get("requested_commands") or outputs.keys())}
    existing = row.get("metrics") or {}
    result = {}
    for key, commands in command_map(vendor).items():
        item = {"label": ITEMS[key], "status": "unknown", "summary": "未采集", "reason": "not_collected",
                "data": None, "commands": commands}
        result[key] = item
        present = [cmd for cmd in commands if cmd in outputs]
        selected = [cmd for cmd in commands if cmd in requested]
        problems = []
        try:
            if key not in ("fanpower", "errors") and any(CLI_ERROR.search(outputs[cmd]) for cmd in present):
                item.update(reason="unsupported", summary="设备不支持")
                continue
            if key in ("cpu", "memory") and number(existing.get(key)):
                data = {"pct": existing[key]}
            elif present:
                if key not in ("fanpower", "errors") and (any(not outputs[cmd].strip() for cmd in present) or any(cmd not in outputs for cmd in selected)):
                    raise ValueError("missing output")
                if key in ("fanpower", "errors"):
                    vals = {}
                    for cmd in commands:
                        try:
                            if cmd not in outputs:
                                problems.append(REASONS["unrecognized" if cmd in selected else "not_collected"])
                                continue
                            if CLI_ERROR.search(outputs[cmd]):
                                problems.append("设备不支持")
                                continue
                            val = (parsers.parse_errors_table(outputs[cmd]) if key == "errors" else
                                   parsers.parse(vendor, "fanpower" if vendor == "huawei" else
                                                 "fan" if cmd == "display fan" else "power", outputs[cmd]))
                            if key == "fanpower" and not val.get("found"):
                                raise ValueError("unknown hardware")
                            vals[cmd] = val
                        except (ValueError, KeyError, TypeError):
                            problems.append("未识别")
                    if not vals:
                        item.update(reason="unsupported" if "设备不支持" in problems else "unrecognized",
                                    summary="、".join(dict.fromkeys(problems)))
                        continue
                    if key == "fanpower":
                        data = parsers.merge_fanpower(*vals.values())
                    else:
                        merged = parsers.merge_errors(vals.get(commands[0], {}), vals.get(commands[1], {}))
                        for port in merged:
                            for cmd, direction in zip(commands, ("inbound", "outbound")):
                                if cmd not in vals:
                                    port[direction] = None
                        data = {"ports": merged, "directions": len(vals)}
                else:
                    data = parsers.parse(vendor, key, outputs[present[0]])
            elif key == "fanpower" and any(existing.get(k, {}).get("found") for k in ("fanpower", "fan", "power") if isinstance(existing.get(k), dict)):
                data = parsers.merge_fanpower(*(existing.get(k) for k in ("fanpower", "fan", "power")))
            elif isinstance(existing.get(key), dict):
                data = existing[key]
            elif selected:
                raise ValueError("missing selected output")
            else:
                continue
            if key in ("cpu", "memory"):
                pct = data.get("pct")
                if not number(pct) or not 0 <= pct <= 100:
                    raise ValueError("invalid percentage")
                status = rules.eval_cpu(pct) if key == "cpu" else rules.eval_memory(pct)
                summary = f"{pct:g}%"
            elif key == "temp":
                readings = data["readings"]
                valid = [r for r in readings if number(r.get("temp"))]
                if not valid:
                    raise ValueError("missing temperature")
                data = dict(data, maximum=max(r["temp"] for r in valid))
                status, summary = rules.eval_temp(valid), f"最高 {data['maximum']:g}℃"
            elif key == "fanpower":
                status = rules.eval_fanpower(data.get("units", []), data.get("found"))
                if status == "unk":
                    raise ValueError("unknown hardware")
                bad = [u for u in data["units"] if u["state"].lower() in rules.BAD_UNIT_STATES]
                summary = "、".join(f"{u['name']}({u['state']})" for u in bad) if bad else f"{len(data['units'])} 个单元正常"
            elif key in ("alarm", "log"):
                count = data.get("count", len(data.get("entries" if key == "alarm" else "flagged", [])))
                status = "warn" if count else "ok"
                summary = f"{count} 条" + ("活跃告警" if key == "alarm" else "警告及以上日志（本次读取范围）")
            elif key == "ports":
                if not data.get("total"):
                    raise ValueError("missing ports")
                status, summary = "ok", f"Up {data['up']}/{data['total']}，链路 Down {data['link_down']}，管理关闭 {data['admin_down']}"
            else:
                status = "warn" if data["ports"] else "ok"
                summary = f"{len(data['ports'])} 个接口存在累计错包（已识别 {data['directions']}/2 个方向）"
            if problems:
                summary += "；部分数据：" + "、".join(dict.fromkeys(problems))
                if status == "ok":
                    status = "unknown"
            item.update(status=status, summary=summary, reason="unrecognized" if problems else "", data=data)
        except (ValueError, KeyError, TypeError, AttributeError):
            item.update(reason="unrecognized", summary="未识别")
    command_issues = [{"command": cmd, "reason": "设备不支持"} for cmd in requested
                      if cmd in outputs and CLI_ERROR.search(outputs[cmd])]
    command_issues.sort(key=lambda issue: issue["command"])
    issues = [f"{item['label']}：{item['summary']}" for item in result.values() if item["status"] in ("warn", "crit")]
    unknown = [item["label"] for item in result.values() if item["status"] == "unknown"]
    overall = ("fail" if row.get("status") == "fail" else "warn" if issues else
               "unknown" if unknown or command_issues or not any(i["status"] == "ok" for i in result.values()) else "ok")
    summary = (row.get("error") or "采集失败") if overall == "fail" else "；".join(issues)
    if not summary:
        summary = "待核实：" + "、".join(unknown) if unknown else "存在不支持的采集命令" if command_issues else "已识别指标未发现异常" if overall == "ok" else "没有可判定的指标"
    return {"schema": 1, "status": overall, "summary": summary, "items": result, "command_issues": command_issues}


def build_report(run, rows):
    devices = []
    for row in rows:
        d = {k: copy.deepcopy(v) for k, v in row.items() if k not in ("outputs", "username", "password", "credentials")}
        d["analysis"] = analyze_device(row)
        d["status"] = d["analysis"]["status"]
        devices.append(d)
    counts = {status: sum(d["status"] == status for d in devices) for status in LABELS}
    resources = {}
    for key in ("cpu", "memory"):
        valid = [{"host": d["host"], "name": d.get("name", d["host"]),
                  "value": d["analysis"]["items"][key]["data"]["pct"]} for d in devices
                 if d["analysis"]["items"][key]["status"] in ("ok", "warn", "crit")]
        resources[key] = {"valid": len(valid), "top": sorted(valid, key=lambda v: (-v["value"], v["host"]))[:10]}
    ports = {key: 0 for key in ("total", "up", "admin_down", "link_down", "devices")}
    for d in devices:
        item = d["analysis"]["items"]["ports"]
        if item["status"] == "ok":
            ports["devices"] += 1
            for key in ("total", "up", "admin_down", "link_down"):
                ports[key] += item["data"][key]
    issues = [{"key": key, "label": label, "count": sum(d["analysis"]["items"][key]["status"] in ("warn", "crit") for d in devices)}
              for key, label in ITEMS.items() if key != "ports"]
    return {"id": run["id"], "started": run.get("started", ""), "state": run.get("state", "done"),
            "total": run.get("total", len(devices)), "completed": len(devices),
            "remaining": max(0, run.get("total", len(devices)) - len(devices)),
            "counts": counts, "resources": resources, "ports": ports, "issues": issues, "devices": devices}


def esc(value):
    return html.escape(str(value if value is not None and value != "" else "—"), quote=True)


def raw_markup(outputs):
    return "".join(f'<details class="report-output"><summary>{esc(cmd)}</summary><pre>{esc(value)}</pre></details>' for cmd, value in (outputs or {}).items()) or '<p>未采集到命令输出。</p>'


def render_body(report, raw_rows=None):
    counts, devices = report["counts"], report["devices"]
    raw = {r["host"]: r.get("outputs", {}) for r in raw_rows or []}
    stamp = report["started"]
    try:
        stamp = datetime.fromisoformat(stamp).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        pass
    cards = "".join(f'<div class="report-stat {key}"><strong>{counts[key]}</strong><span>{label}</span></div>' for key, label in LABELS.items())
    legend = "".join(f'<span class="report-label {key}">{label} {counts[key]}</span>' for key, label in LABELS.items())
    segments, offset = [], 0
    colors = {"ok": "#23795f", "warn": "#b37a22", "unknown": "#87958e", "fail": "#b34c4c"}
    for key in LABELS:
        share = counts[key] / max(1, len(devices)) * 100
        segments.append(f'{colors[key]} {offset:g}% {offset + share:g}%')
        offset += share
    ring = f'<div class="report-ring" style="background:conic-gradient({",".join(segments) if devices else "#e8edea 0% 100%"})"><span><strong>{len(devices)}</strong>已返回设备</span></div>'
    resources = []
    for key, label in (("cpu", "CPU"), ("memory", "内存")):
        resource = report["resources"][key]
        bars = "".join(f'<div class="report-bar-row"><span title="{esc(r["host"])}">{esc(r["name"])}</span><div class="report-meter"><i style="width:{r["value"]:g}%;background:{"#b34c4c" if r["value"] >= 90 else "#b37a22" if r["value"] >= 80 else "#23795f"}"></i></div><b>{r["value"]:g}%</b></div>' for r in resource["top"])
        resources.append(f'<h4>{label} · 有效样本 {resource["valid"]} 台</h4>{bars or "<p>暂无有效读数</p>"}')
    port = report["ports"]
    portbars = "".join(f'<span style="width:{port[key] / max(1, port["total"]) * 100:g}%;background:{color}" title="{label} {port[key]}"></span>' for key, label, color in (("up", "Up", "#23795f"), ("admin_down", "管理关闭", "#a4afa9"), ("link_down", "链路 Down", "#d6b47a")))
    issuebars = "".join(f'<div class="report-bar-row"><span>{esc(i["label"])}</span><div class="report-meter"><i style="width:{i["count"] / max(1, len(devices)) * 100:g}%;background:#b37a22"></i></div><b>{i["count"]} 台</b></div>' for i in report["issues"])
    charts = f'''<div class="report-charts"><section><h3>设备状态分布</h3>{ring}<div class="report-legend">{legend}</div></section>
    <section><h3>资源使用 Top 10</h3><p>80% 提醒 · 90% 严重 · 未识别值不计为零</p>{''.join(resources)}</section>
    <section><h3>端口状态分布</h3><p>已识别 {port['devices']} 台 · {port['total']} 个接口</p><div class="report-stacked">{portbars}</div><div class="report-legend"><span>Up {port['up']}</span><span>管理关闭 {port['admin_down']}</span><span>链路 Down {port['link_down']}</span></div><p>链路 Down 仅作统计，不直接告警。</p></section>
    <section><h3>异常涉及设备数</h3><p>同一设备可计入多个类别；错包为累计值。</p>{issuebars}</section></div>'''
    table, details = [], []
    for index, d in enumerate(devices):
        a = d["analysis"]
        def val(key):
            item = a["items"][key]
            if key in ("cpu", "memory") and item["data"] is not None:
                return f'{item["data"]["pct"]:g}%'
            if key == "temp" and item["data"] is not None:
                return f'{item["data"]["maximum"]:g}℃'
            if key == "ports" and item["data"] is not None:
                return f'{item["data"]["up"]}/{item["data"]["total"]}'
            return REASONS.get(item["reason"], "未识别")
        detail_id = f'report-device-{index}'
        attributes = f'data-report-status="{esc(d["status"])}" data-report-group="{esc(d.get("group") or "未分组")}" data-report-query="{esc(" ".join(str(d.get(k, "")) for k in ("name", "host", "group", "model", "vendor"))).lower()}"'
        table.append(f'<tr {attributes}><td><button type="button" class="report-jump" data-report-jump="{detail_id}">{esc(d.get("name") or d["host"])}</button><small>{esc(d["host"])}</small></td><td>{esc({"huawei":"华为","hp_comware":"H3C"}.get(d.get("vendor"), "未识别"))}<small>{esc(d.get("model"))}</small></td><td><span class="report-label {d["status"]}">{LABELS[d["status"]]}</span></td>{"".join(f"<td>{esc(val(k))}</td>" for k in ("cpu","memory","temp","ports"))}<td class="report-summary-text">{esc(a["summary"])}</td></tr>')
        itemrows = "".join(f'<tr><td>{esc(i["label"])}</td><td>{esc({"ok":"正常","warn":"提醒","crit":"严重","unknown":REASONS.get(i["reason"],"待核实")}[i["status"]])}</td><td>{esc(i["summary"])}</td><td>{esc(" / ".join(i["commands"]))}</td></tr>' for i in a["items"].values())
        evidence = []
        for key in ("temp", "fanpower", "alarm", "log", "ports", "errors"):
            item = a["items"][key]
            if item["data"] is not None:
                import json
                evidence.append(f'<details class="report-output"><summary>{esc(item["label"])} · 结构化证据</summary><pre>{esc(json.dumps(item["data"], ensure_ascii=False, indent=2))}</pre></details>')
        commandnotes = "".join(f'<p class="report-note">{esc(issue["command"])}：{esc(issue["reason"])}</p>' for issue in a.get("command_issues", []))
        details.append(f'''<details class="report-device" id="{detail_id}" data-report-host="{esc(d['host'])}"><summary>{esc(d.get('name') or d['host'])} · {esc(d['host'])} <span class="report-label {d['status']}">{LABELS[d['status']]}</span></summary><div class="report-device-body"><p>型号 {esc(d.get('model'))} · 版本 {esc(d.get('version'))} · 运行时间 {esc(d.get('uptime'))}<br>SN {esc(d.get('serial_number'))} · 连接 {esc(d.get('transport','').upper() or '未记录')} · 分组 {esc(d.get('group'))}</p><p class="report-note">{esc(d.get('error') or '无连接说明')}</p><div class="report-scroll"><table><thead><tr><th>指标</th><th>结论</th><th>摘要</th><th>命令依据</th></tr></thead><tbody>{itemrows}</tbody></table></div>{''.join(evidence)}{commandnotes}<h4>原始命令输出</h4><div class="report-raw" data-loaded="{'true' if raw_rows is not None else 'false'}">{raw_markup(raw.get(d['host'],{})) if raw_rows is not None else '<p>展开设备详情后加载完整输出。</p>'}</div></div></details>''')
    groups = sorted({d.get("group") or "未分组" for d in devices})
    options = "".join(f'<option value="{esc(g)}">{esc(g)}</option>' for g in groups)
    return f'''<div class="inspection-report" data-run-id="{esc(report['id'])}"><header><h2>交换机巡检报告</h2><p>{esc(stamp)} · 计划 {report['total']} 台 · 已返回 {report['completed']} 台 · 未执行 {report['remaining']} 台 · {"任务已取消" if report['state']=='cancelled' else "任务已完成"}</p></header><div class="report-stats">{cards}</div><p class="report-insight">{counts['warn']} 台需关注，{counts['unknown']} 台待核实，{counts['fail']} 台采集失败。仅分析本次任务，不推断历史趋势。</p>{charts}<section class="report-table-section"><h3>设备简版汇总</h3><div class="report-filters"><label>搜索<input data-report-search placeholder="设备、IP、型号或分组"></label><label>状态<select data-report-filter="status"><option value="">全部状态</option>{''.join(f'<option value="{k}">{v}</option>' for k,v in LABELS.items())}</select></label><label>分组<select data-report-filter="group"><option value="">全部分组</option>{options}</select></label><span data-report-count>共 {len(devices)} 台</span></div><div class="report-scroll"><table class="report-summary"><thead><tr><th>设备 / IP</th><th>平台 / 型号</th><th>结论</th><th>CPU</th><th>内存</th><th>最高温度</th><th>Up / 总数</th><th>简短分析</th></tr></thead><tbody>{''.join(table)}</tbody></table></div><p data-report-empty hidden>没有匹配的设备。</p></section><section class="report-details"><h3>详细结果</h3><p>点击上方设备名称可定位详情；原始输出默认折叠。</p>{''.join(details) or '<p>本次没有返回设备结果。</p>'}</section></div>'''


def render_document(report, rows, resources):
    root = Path(resources)
    css = (root / "report.css").read_text(encoding="utf-8")
    js = (root / "report-view.js").read_text(encoding="utf-8")
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>交换机巡检报告</title><style>body{margin:0;padding:32px;background:#f4f6f5;font:14px/1.6 "Segoe UI","Microsoft YaHei",sans-serif;color:#24372e}body>.inspection-report{max-width:1400px;margin:auto}</style>'
            f'<style>{css}</style></head><body>{render_body(report, rows)}<script type="text/javascript">{js}\nReportView.mount(document.querySelector(".inspection-report"));</script></body></html>')
