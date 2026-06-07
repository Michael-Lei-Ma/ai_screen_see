@echo off
REM 设置命令行编码为UTF-8，确保中文正常显示
chcp 65001 >nul
REM 启用延迟变量扩展，允许在代码块中使用变量
setlocal enabledelayedexpansion

REM 设置服务目录为当前脚本所在目录
set "SERVICE_DIR=%~dp0.."
set "SERVICE_DIR=%SERVICE_DIR:~0,-1%"

REM 检查SystemScanService.exe是否已在运行
tasklist /fi "imagename eq SystemScanService.exe" | find "SystemScanService.exe" >nul
set "SERVICE_RUNNING=0"
if !errorlevel! equ 0 set "SERVICE_RUNNING=1"

REM 隐藏窗口运行机制：如果未传入hidden参数，则通过PowerShell隐藏窗口重新启动自身
if "%~1"=="hidden" goto :MAIN

REM 添加管理员权限检查
net session >nul 2>&1
if %errorlevel% neq 0 (
    REM 以管理员身份重新启动
    powershell -WindowStyle Hidden -Command "Start-Process '%~f0' -ArgumentList 'hidden' -Verb RunAs -WindowStyle Hidden"
    exit /b
)

REM 使用PowerShell隐藏窗口重新启动当前脚本，并传递hidden参数
powershell -WindowStyle Hidden -Command "Start-Process '%~f0' -ArgumentList 'hidden' -WindowStyle Hidden"
REM 退出当前可见的脚本实例
exit /b 0

:MAIN
if !SERVICE_RUNNING! equ 1 (
    REM 服务已在运行中直接退出
    exit /b 0
)

REM 如果进程不存在，则启动服务
wscript "%SERVICE_DIR%\start-hidden.vbs"
exit /b 0