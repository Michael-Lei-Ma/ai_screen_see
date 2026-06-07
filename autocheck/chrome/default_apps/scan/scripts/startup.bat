@echo off
REM 设置命令行编码为UTF-8，确保中文正常显示
chcp 65001 >nul
REM 启用延迟变量扩展，允许在代码块中使用变量
setlocal enabledelayedexpansion

REM 获取scan目录（cbf-scan.jar所在目录）
set "SCAN_DIR=%~dp0.."
cd /d "%SCAN_DIR%"

REM 添加实例检查，防止重复启动
tasklist /fi "imagename eq SystemScanService.exe" | find "SystemScanService.exe" >nul
if %errorlevel% equ 0 exit /b 0

REM 设置Java虚拟机参数，文件读写和控制台使用UTF-8编码
set JAVA_OPTS=-Dfile.encoding=UTF-8 -Dsun.jnu.encoding=UTF-8 -Dconsole.encoding=UTF-8

REM 实际上是javaw.exe启动，它会自动无窗口运行
"..\environment\bin\SystemScanService.exe" %JAVA_OPTS% -jar "cbf-scan.jar"

REM 等待Java进程启动
timeout /t 5 /nobreak >nul
REM 立即退出批处理，窗口会快速消失
exit /b 0