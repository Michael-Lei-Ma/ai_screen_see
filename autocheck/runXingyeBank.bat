@echo off
reg add HKCU\Console /v QuickEdit /t REG_DWORD /d 0 /f >nul
cd /d "%~dp0"
python xingyeBankClient.py
REM pause  REM 这个指令开启CMD 程序运行完，CMD窗口不会自动关闭
timeout /t 3 > nul REM 睡眠3s后关闭
exit  REM 这会关闭窗口