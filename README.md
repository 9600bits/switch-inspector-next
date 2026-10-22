# Switch Inspector Next

Switch Inspector Next 是一个面向 Windows 桌面环境的交换机巡检工具，支持通过 SSH 巡检华为 VRP 和 H3C Comware 设备。

## 功能

- 管理交换机资产，支持 Excel 导入和导出。
- SSH 登录后先执行 `display version`，根据设备实际返回内容识别华为或 H3C 平台。
- 根据识别到的平台设置分页方式，再执行巡检命令。
- 在设置页分别维护华为和 H3C 命令清单，支持新增、编辑、排序、启停和恢复默认命令。
- 每次巡检开始前展示本次启用的命令，人工确认后才连接设备。
- 每个并发线程提供一个实时命令窗口，显示当前设备、命令和输出。
- 并发数限制为 1–16，默认 5；取消任务后已建立的 SSH 会话会正常结束。
- 可选采集设备 SN。SN 采集失败只记录为未识别，不影响其他巡检结果。
- 资产列表支持搜索和筛选，筛选结果一次显示，不做分页。
- 巡检结果、设备详情和报告归档保存在本机。

## 运行要求

- Windows 10 或更高版本
- Python 3.10 或更高版本（从源码运行时）
- Microsoft Edge WebView2 Runtime

WebView2 是桌面界面运行所需的系统组件。打包后的 EXE 不包含 WebView2，其他 Windows 电脑首次运行前需要安装它。

## 从源码运行

```powershell
python -m pip install -r requirements.txt
python main.py
```

启动演示工作区：

```powershell
python main.py --demo
```

演示工作区只使用示例数据，不会连接真实设备。

## 构建 EXE

在 Windows PowerShell 中执行：

```powershell
.\build.bat
```

输出文件为：

```text
dist\SwitchInspectorNext.exe
```

EXE 使用 PyInstaller 的单文件、无控制台模式构建，运行时仍需要系统 WebView2 Runtime。构建脚本已排除 Qt、CEF、Tk 等未使用模块，以减少体积。

## 测试

运行后端和单元测试：

```powershell
python -m pytest -q
```

运行浏览器端 UI 测试前，先启动静态文件服务：

```powershell
python -m http.server 8767 --directory ui
python tests/test_ui.py
```

UI 测试使用演示数据，覆盖资产搜索、筛选、命令确认、并发控制台、任务取消与完成、报告页面和空工作区。

## 数据位置

应用数据默认保存在：

```text
%LOCALAPPDATA%\SwitchInspectorNext
```

设备凭据由 Windows DPAPI 加密保存。命令清单按华为和 H3C 平台分别保存。

## 采集说明

设备保持在 SSH 用户视图中，应用不会自动进入配置模式或提权。默认分页命令为：

- 华为：`screen-length 0 temporary`
- H3C：`screen-length disable`

不同型号或版本可能存在命令差异，建议在设置页按现场设备实际情况人工核对和调整命令清单。
