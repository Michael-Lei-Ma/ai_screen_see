@echo off
reg add HKCU\Console /v QuickEdit /t REG_DWORD /d 0 /f >nul
cd /d "%~dp0"
python Q_ShangQi_Request.py
pause