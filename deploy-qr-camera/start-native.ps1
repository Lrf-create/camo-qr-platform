$ErrorActionPreference = 'Stop'
$nativeRoot = Join-Path $PSScriptRoot 'native'
$runtime = Join-Path $PSScriptRoot 'python\python.exe'
$supervisor = Join-Path $nativeRoot 'supervisor.py'
if (-not (Test-Path -LiteralPath (Join-Path $nativeRoot 'migration-complete.json'))) {
    throw 'Local database migration is not complete. See native logs.'
}
$nativeInstallation = Join-Path $nativeRoot 'installation.json'
if (-not (Test-Path -LiteralPath $nativeInstallation)) {
    @{ postgres_home = 'D:\CamoScanPlatformNative' } | ConvertTo-Json | Set-Content -LiteralPath $nativeInstallation -Encoding UTF8
}
if (-not (Get-Process -Name 'CamoStudio' -ErrorAction SilentlyContinue)) {
    $camoApp = Get-StartApps | Where-Object { $_.Name -eq 'Camo Studio' } | Select-Object -First 1
    if ($camoApp) {
        Start-Process -FilePath 'explorer.exe' -ArgumentList ('shell:AppsFolder\' + $camoApp.AppID) -WindowStyle Hidden
    } else {
        Write-Host 'Camo Studio was not found. Open the installed camera application manually.'
    }
}
$alreadyRunning = $false
$pidPath = Join-Path $nativeRoot 'supervisor.pid'
if (Test-Path -LiteralPath $pidPath) {
    $nativeProcessId = [int](Get-Content -LiteralPath $pidPath -Raw).Trim()
    $nativeProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$nativeProcessId" -ErrorAction SilentlyContinue
    $alreadyRunning = $nativeProcess -and $nativeProcess.CommandLine -and $nativeProcess.CommandLine.Contains($supervisor)
}
if (-not $alreadyRunning) {
    foreach ($nativePort in @(8000, 8001)) {
        $occupied = Get-NetTCPConnection -LocalPort $nativePort -State Listen -ErrorAction SilentlyContinue
        if ($occupied) { throw "Port $nativePort is occupied. Stop the old platform before starting the local application." }
    }
    # The Windows task starts outside the launcher's process tree, so closing
    # the terminal or the application that invoked this script cannot kill it.
    $nativeTaskName = 'CamoScanPlatform'
    $nativeTask = Get-ScheduledTask -TaskName $nativeTaskName -ErrorAction SilentlyContinue
    $nativeBackgroundRuntime = Join-Path $PSScriptRoot 'python\pythonw.exe'
    if (-not $nativeTask) {
        $nativeAction = New-ScheduledTaskAction -Execute $nativeBackgroundRuntime -Argument ('"' + $supervisor + '"') -WorkingDirectory $PSScriptRoot
        $nativeUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        $nativePrincipal = New-ScheduledTaskPrincipal -UserId $nativeUser -LogonType Interactive -RunLevel Limited
        $nativeSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
        Register-ScheduledTask -TaskName $nativeTaskName -Action $nativeAction -Principal $nativePrincipal -Settings $nativeSettings -Description 'Camo local platform; desktop launcher starts this task on demand.' -ErrorAction Stop | Out-Null
    } elseif ($nativeTask.Actions.Execute -ne $nativeBackgroundRuntime -or $nativeTask.Actions.Arguments -ne ('"' + $supervisor + '"')) {
        throw 'The CamoScanPlatform task points to a different installation. No existing task was changed.'
    }
    Start-ScheduledTask -TaskName $nativeTaskName -ErrorAction Stop
}
for ($nativeAttempt = 0; $nativeAttempt -lt 30; $nativeAttempt++) {
    try {
        $webReady = Invoke-WebRequest 'http://127.0.0.1:8000/display/sterile-supply/' -UseBasicParsing -TimeoutSec 2
        $qrReady = Invoke-RestMethod 'http://127.0.0.1:8001/database/health' -TimeoutSec 2
        if ($webReady.StatusCode -eq 200 -and $qrReady.status -eq 'ok') {
            Write-Host 'Camo platform and camera capture started locally. Docker is not required.'
            Write-Host 'Connect your phone in Camo Studio before scanning. No webpage is opened automatically.'
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 1
}
throw 'Local startup did not complete. See native\supervisor.log and native\launcher-error.log.'
