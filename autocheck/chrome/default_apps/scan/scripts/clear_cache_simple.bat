@echo off
chcp 65001 >nul
echo 正在清除图标缓存...

REM 杀死资源管理器
taskkill /f /im explorer.exe >nul 2>&1

REM 删除图标缓存文件
del /f /q "%localappdata%\IconCache.db" >nul 2>&1
del /f /q "%localappdata%\Microsoft\Windows\Explorer\iconcache_*.db" >nul 2>&1

REM 重启资源管理器
start explorer.exe

echo 图标缓存已清除！
echo 请重新启动你的服务查看效果
pause