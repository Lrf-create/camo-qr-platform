# Create or refresh the desktop shortcut for the local POC platform.
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TargetPath = Join-Path $ProjectRoot "scripts\start_platform.cmd"
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutName = -join ([char[]](0x533B,0x7528,0x5668,0x68B0,0x7BA1,0x7406,0x5E73,0x53F0)) + ".lnk"
$ShortcutDescription = -join ([char[]](0x542F,0x52A8,0x533B,0x7528,0x5668,0x68B0,0x7BA1,0x7406,0x5E73,0x53F0,0x0020,0x0050,0x004F,0x0043))
$ShortcutPath = Join-Path $DesktopPath $ShortcutName

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = $ShortcutDescription
$Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
$Shortcut.Save()

Write-Host "Desktop shortcut created: $ShortcutPath" -ForegroundColor Green
