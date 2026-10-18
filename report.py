"""HTML 报告渲染：单文件、内嵌 CSS、无外部依赖，可离线转发。"""

import html
from datetime import datetime

from rules import ITEM_LABELS

# 状态 -> (中文标签, CSS 类名)
STATUS_META = {
    "ok":   ("正常", "lv-ok"),
    "warn": ("警告", "lv-warn"),
    "crit": ("严重", "lv-crit"),
    "fail": ("失联", "lv-fail"),
    "info": ("提示", "lv-info"),
    "unk":  ("未知", "lv-unk"),
}

ITEM_ORDER = ["version", "cpu", "memory", "temp", "fanpower",
              "alarm", "log", "ports", "errors"]

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
       background: #f1f5f9; color: #1e293b; padding: 24px; font-size: 14px; }
.wrap { max-width: 1080px; margin: 0 auto; }
h1 { font-size: 22px; margin-bottom: 4px; }
.sub { color: #64748b; margin-bottom: 20px; }
.cards { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
.card { flex: 1; min-width: 120px; background: #fff; border-radius: 10px;
        padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.card .num { font-size: 26px; font-weight: 700; }
.card .lbl { color: #64748b; font-size: 12px; }
.c-ok .num { color: #16a34a; } .c-warn .num { color: #d97706; }
.c-crit .num { color: #dc2626; } .c-fail .num { color: #7f1d1d; }
.device { background: #fff; border-radius: 10px; padding: 16px 18px;
          margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.dev-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
            margin-bottom: 12px; }
.dev-head h2 { font-size: 16px; }
.meta { color: #64748b; font-size: 12px; }
.badge { padding: 2px 10px; border-radius: 999px; font-size: 12px;
         font-weight: 600; white-space: nowrap; }
.lv-ok   { background: #dcfce7; color: #15803d; }
.lv-warn { background: #fef3c7; color: #b45309; }
.lv-crit { background: #fee2e2; color: #b91c1c; }
.lv-fail { background: #7f1d1d; color: #fecaca; }
.lv-info { background: #e2e8f0; color: #475569; }
.lv-unk  { background: #f1f5f9; color: #94a3b8; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #f1f5f9;
         vertical-align: top; }
th { color: #64748b; font-weight: 500; font-size: 12px; background: #f8fafc; }
td.val { word-break: break-all; }
.failmsg { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c;
           padding: 10px 14px; border-radius: 8px; margin-top: 8px; }
details { margin-top: 10px; }
summary { cursor: pointer; color: #2563eb; font-size: 13px; user-select: none; }
pre { background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 8px;
      overflow-x: auto; font-size: 12px; line-height: 1.5; margin-top: 6px;
      max-height: 360px; overflow-y: auto; }
.footer { text-align: center; color: #94a3b8; font-size: 12px; margin-top: 28px; }
@media print { body { background: #fff; padding: 0; }
               .device { break-inside: avoid; } }
"""


def _esc(s):
    return html.escape(str(s), quote=True)


def _badge(status):
    label, cls = STATUS_META.get(status, ("未知", "lv-unk"))
    return f'<span class="badge {cls}">{label}</span>'


def _detail_entries(title, entries, limit=60):
    """折叠展示文本条目列表。"""
    if not entries:
        return ""
    lines = "\n".join(_esc(e) for e in entries[:limit])
    more = f"\n…（其余 {len(entries) - limit} 条省略）" if len(entries) > limit else ""
    return (f"<details><summary>{_esc(title)}（{len(entries)} 条）</summary>"
            f"<pre>{lines}{more}</pre></details>")


def _ports_table(detail):
    if not detail or not detail.get("notable"):
        return ""
    rows = "".join(
        f"<tr><td>{_esc(p['name'])}</td><td>{_esc(p['phy'])}</td></tr>"
        for p in detail["notable"][:100])
    extra = f"<p class='meta'>（仅列异常，共 {len(detail['notable'])} 个）</p>" \
        if len(detail["notable"]) > 100 else ""
    return (f"<details><summary>链路 down 的端口（{len(detail['notable'])} 个）</summary>"
            f"{extra}<table><tr><th>接口</th><th>状态</th></tr>{rows}</table></details>")


def _errors_table(detail):
    if not detail:
        return ""
    rows = "".join(
        f"<tr><td>{_esc(b['port'])}</td><td>{b['inbound']}</td>"
        f"<td>{b['outbound']}</td></tr>" for b in detail[:50])
    return (f"<details><summary>错包端口明细</summary>"
            f"<table><tr><th>接口</th><th>入向错误合计</th><th>出向错误合计</th></tr>"
            f"{rows}</table></details>")


def _device_section(res):
    dev = res.device
    _, cls = STATUS_META.get(res.status, STATUS_META["unk"])
    head = (
        f'<div class="dev-head"><h2>{_esc(dev.name)}</h2>'
        f'{_badge(res.status)}'
        f'<span class="meta">{_esc(dev.host)}｜{_esc(dev.group)}｜'
        f'{"华为 VRP" if dev.vendor == "huawei" else "华三 Comware"}</span></div>'
    )
    if res.status == "fail":
        return f'<div class="device">{head}<div class="failmsg">✗ {_esc(res.error)}</div></div>'

    rows = []
    for key in ITEM_ORDER:
        item = res.items.get(key)
        if item is None:
            continue
        label = _esc(ITEM_LABELS.get(item.key, item.key))
        rows.append(
            f"<tr><th style='width:130px'>{label}</th>"
            f"<td class='val'>{_esc(item.display)}</td><td style='width:64px'>"
            f"{_badge(item.status)}</td></tr>")
    body = f"<table>{''.join(rows)}</table>"

    extras = []
    ports_item = res.items.get("ports")
    if ports_item and ports_item.detail and ports_item.detail.get("link_down"):
        extras.append(_ports_table(ports_item.detail))
    err_item = res.items.get("errors")
    if err_item and err_item.detail:
        extras.append(_errors_table(err_item.detail))
    alarm_item = res.items.get("alarm")
    if alarm_item and alarm_item.detail:
        extras.append(_detail_entries("活跃告警原文", alarm_item.detail))
    log_item = res.items.get("log")
    if log_item and log_item.detail:
        extras.append(_detail_entries("警告级及以上日志", log_item.detail))

    raws = []
    cmd_names = {"version": "display version", "cpu": "cpu-usage",
                 "memory": "memory", "temp": "environment",
                 "fanpower": "device/fan/power", "alarm": "alarm active",
                 "log": "logbuffer", "ports": "interface brief",
                 "err_in": "counters errors inbound",
                 "err_out": "counters errors outbound"}
    raw_blocks = "".join(
        f"<details><summary>原始输出：{_esc(cmd_names.get(k, k))}</summary>"
        f"<pre>{_esc(raw[:4000])}</pre></details>"
        for k, raw in res.raws.items() if raw.strip())
    if raw_blocks:
        extras.append(f"<details><summary>全部原始输出</summary>{raw_blocks}</details>")

    return (f'<div class="device">{head}{body}'
            f"{''.join(extras)}</div>")


def build_html(results, generated_at=None):
    """results: list[DeviceResult] → 完整 HTML 字符串。"""
    generated_at = generated_at or datetime.now()
    counts = {"ok": 0, "warn": 0, "crit": 0, "fail": 0}
    for r in results:
        if r.status == "ok":
            counts["ok"] += 1          # info/unk 并入正常
        elif r.status == "fail":
            counts["fail"] += 1
        elif r.status == "crit":
            counts["crit"] += 1
        elif r.status == "warn":
            counts["warn"] += 1

    cards = (
        '<div class="cards">'
        f'<div class="card c-ok"><div class="num">{counts["ok"]}</div><div class="lbl">正常</div></div>'
        f'<div class="card c-warn"><div class="num">{counts["warn"]}</div><div class="lbl">警告</div></div>'
        f'<div class="card c-crit"><div class="num">{counts["crit"]}</div><div class="lbl">严重</div></div>'
        f'<div class="card c-fail"><div class="num">{counts["fail"]}</div><div class="lbl">失联</div></div>'
        "</div>"
    )
    sections = "".join(_device_section(r) for r in results)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>交换机巡检报告 {generated_at:%Y-%m-%d %H:%M}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
<h1>交换机自动巡检报告</h1>
<p class="sub">生成时间：{generated_at:%Y-%m-%d %H:%M:%S}　共 {len(results)} 台设备</p>
{cards}
{sections}
<p class="footer">switch-inspector 自动生成 · 阈值：CPU≥80% 警告 ≥90% 严重 · 内存≥80% 警告 ≥90% 严重 · 温度≥60℃ 警告 ≥75℃ 严重</p>
</div>
</body>
</html>"""
