"""设备清单（Excel）读取、校验与模板生成。

清单格式（第一个工作表，第 1 行为表头）：
  设备名称 | IP地址 | 品牌 | SSH端口 | 用户名 | 密码 | 分组

品牌支持：华为 / huawei / H3C / 华三 / comware（不区分大小写）
"""

from pathlib import Path

from openpyxl import Workbook, load_workbook

HEADERS = ["设备名称", "IP地址", "品牌", "SSH端口", "用户名", "密码", "分组"]

_BRAND_MAP = {
    "huawei": "huawei", "华为": "huawei",
    "h3c": "hp_comware", "华三": "hp_comware", "hp": "hp_comware",
    "comware": "hp_comware", "新华三": "hp_comware",
}

_INSTRUCTION = (
    "【使用说明】\n"
    "1. 每行一台交换机，填写：设备名称、IP地址、品牌（华为/H3C）、SSH端口（默认22）、用户名、密码；\n"
    "2. “分组”列可选，用于报告归类（如 总部/分支）；\n"
    "3. 示例行请删除或修改后保存，再运行巡检工具；\n"
    "4. 品牌可填：华为 / H3C（不区分大小写）。\n"
)


class DeviceListError(Exception):
    """清单格式或内容错误。"""


class Device:
    def __init__(self, name, host, vendor, port, username, password, group=""):
        self.name = name
        self.host = host
        self.vendor = vendor          # huawei / hp_comware
        self.port = port
        self.username = username
        self.password = password
        self.group = group or "未分组"

    def __repr__(self):
        return f"<Device {self.name} {self.host} {self.vendor}>"


def _normalize_brand(raw):
    key = str(raw).strip().lower()
    return _BRAND_MAP.get(key)


def load(path: Path):
    """读取并校验设备清单，返回 Device 列表。有问题行跳过并收集错误信息。"""
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        raise DeviceListError("Excel 是空的，没有任何数据")

    errors, devices = [], []
    for idx, row in enumerate(rows[1:], start=2):  # 第 1 行是表头
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue
        vals = ["" if c is None else str(c).strip() for c in row[:7]]
        while len(vals) < 7:
            vals.append("")
        name, host, brand_raw, port_raw, user, pwd, group = vals

        problems = []
        if not host:
            problems.append("缺少 IP 地址")
        if not user:
            problems.append("缺少用户名")
        if not pwd:
            problems.append("缺少密码")
        vendor = _normalize_brand(brand_raw)
        if not vendor:
            problems.append(f"品牌无法识别: “{brand_raw}”（应填 华为 或 H3C）")
        try:
            port = int(float(port_raw)) if port_raw else 22
        except ValueError:
            problems.append(f"SSH 端口不是数字: “{port_raw}”")
            port = None

        if problems:
            errors.append(f"第 {idx} 行（{name or host or '未命名'}）：{'；'.join(problems)}")
            continue
        devices.append(Device(name or host, host, vendor, port, user, pwd, group))

    if errors:
        raise DeviceListError("清单存在以下问题，请修正后重试：\n  " + "\n  ".join(errors))
    if not devices:
        raise DeviceListError("清单里没有有效设备（只有表头或空行）")
    return devices


def ensure_template(path: Path) -> bool:
    """devices.xlsx 不存在时生成模板。返回是否新建了文件。"""
    if path.exists():
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = "设备清单"
    ws.append(HEADERS)
    ws.append(["核心交换机A", "192.168.1.1", "华为", 22, "admin", "请改成真实密码", "总部"])
    ws.append(["接入交换机B", "192.168.1.2", "H3C", 22, "admin", "请改成真实密码", "分支"])
    # 列宽
    widths = [18, 16, 8, 10, 12, 20, 10]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w

    info = wb.create_sheet("说明")
    info.column_dimensions["A"].width = 80
    for i, line in enumerate(_INSTRUCTION.strip().splitlines(), start=1):
        info.cell(row=i, column=1, value=line)

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return True
