@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-native.ps1"
if errorlevel 1 (
  echo 启动失败，请查看 native 目录内的 supervisor.log 和 launcher-error.log。
  pause
  exit /b 1
)
