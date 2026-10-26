@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-native.ps1" -OpenDisplay
if errorlevel 1 (
  echo 启动失败，请查看 native 目录中的 logon-startup.log 和 kiosk.log。
  pause
  exit /b 1
)
