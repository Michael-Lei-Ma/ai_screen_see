@echo off
chcp 65001 >nul

taskkill /f /im SystemScanService.exe >nul 2>&1

schtasks /delete /tn "SystemScanService_AutoStart" /f >nul 2>&1

REM 清理与当前服务相关的cmd进程
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq cmd.exe" /fo csv ^| findstr /i "service-manager startup"') do (
    taskkill /f /pid %%i >nul 2>&1
)

REM 清理conhost进程（控制台主机）
taskkill /f /im conhost.exe >nul 2>&1

exit /b 0