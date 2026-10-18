# Switch Inspector Next

Windows desktop application for inspecting Huawei and H3C network switches over SSH.

## Features

- Manage switch assets and import or export Excel workbooks.
- Detect the device platform from `display version` before collecting data.
- Configure Huawei and H3C command lists, with confirmation before each run.
- Show live command output in one console per worker thread.
- Collect version, uptime, interfaces, VLANs, MAC addresses, ARP entries, and optional serial numbers.
- Store application data under `%LOCALAPPDATA%\SwitchInspectorNext`.

## Run from source

Requires Python 3.10 or later and Microsoft Edge WebView2 Runtime.

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Build the Windows executable

Run `build.bat` on Windows. The output is written to `dist\SwitchInspectorNext.exe`.
The executable uses the system WebView2 Runtime, which may need to be installed separately on Windows 10 systems.

## Tests

```powershell
python -m pytest
```

