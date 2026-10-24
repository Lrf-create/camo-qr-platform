# Windows desktop entry point for the local POC platform.
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Url = "http://127.0.0.1:8000/"
$HostAddress = "127.0.0.1"
$Port = 8000

Set-Location -LiteralPath $ProjectRoot
$env:DJANGO_SETTINGS_MODULE = "config.settings.dev"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Medical Device Management POC" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host "URL: $Url"
Write-Host ""
Write-Host "Django will auto-start the A/B submission processor after the web service starts." -ForegroundColor Yellow
Write-Host "Keep this window open. Closing it stops the platform." -ForegroundColor Yellow
Write-Host ""

$PortInUse = Test-NetConnection -ComputerName $HostAddress -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
if ($PortInUse) {
    Write-Host "$Url is already reachable. Opening the browser now." -ForegroundColor Yellow
    Start-Process $Url
    Write-Host "If this is an old server instance, close the window using port 8000 first, then restart." -ForegroundColor Yellow
    Read-Host "Press Enter to close this window"
    exit 0
}

$BrowserJob = Start-Job -ScriptBlock {
    param($TargetUrl)
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $TargetUrl -UseBasicParsing -TimeoutSec 1
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Start-Process $TargetUrl
                return
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
} -ArgumentList $Url

try {
    python .\manage.py runserver 127.0.0.1:8000
} finally {
    if ($BrowserJob.State -eq "Running") {
        Stop-Job $BrowserJob | Out-Null
    }
    Remove-Job $BrowserJob -Force -ErrorAction SilentlyContinue
    Write-Host ""
    Write-Host "Platform stopped." -ForegroundColor Yellow
    Read-Host "Press Enter to close this window"
}
