@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SwitchInspectorNext --add-data "ui;ui" --exclude-module PyQt5 --exclude-module PySide6 --exclude-module PySide2 --exclude-module qtpy --exclude-module cefpython3 --exclude-module tkinter --exclude-module wx main.py
pause
