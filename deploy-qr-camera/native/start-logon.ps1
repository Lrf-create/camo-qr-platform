$ErrorActionPreference = 'Stop'
$launchRoot = Split-Path -Parent $PSScriptRoot
$logPath = Join-Path $PSScriptRoot 'logon-startup.log'
try {
    Add-Content -LiteralPath $logPath -Encoding UTF8 -Value "$(Get-Date -Format o) Login startup entered."
    & (Join-Path $launchRoot 'start-native.ps1') -OpenDisplay *>> $logPath
    if ($LASTEXITCODE -ne 0) { throw "Launcher exited with code $LASTEXITCODE" }
} catch {
    Add-Content -LiteralPath $logPath -Encoding UTF8 -Value $_.Exception.ToString()
    exit 1
}
