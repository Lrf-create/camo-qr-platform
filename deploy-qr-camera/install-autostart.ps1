param([switch]$Disable, [switch]$Remove)
$ErrorActionPreference = 'Stop'
$taskName = 'CamoScanPlatform-Logon'
$scriptPath = Join-Path $PSScriptRoot 'native\start-logon.ps1'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($Disable -and $Remove) { throw 'Choose Disable or Remove, not both.' }
if ($task -and $task.Actions.Arguments -notlike ('*"' + $scriptPath + '"*')) {
    throw 'An existing login task belongs to another installation. No task was changed.'
}
if ($Remove) {
    if ($task) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false }
    Write-Host 'Login startup removed. Data and running services are unchanged.'
    exit 0
}
if ($Disable) {
    if ($task) { Disable-ScheduledTask -TaskName $taskName | Out-Null }
    Write-Host 'Login startup disabled. Data and running services are unchanged.'
    exit 0
}
foreach ($required in @('python\python.exe','python\pythonw.exe','native\kiosk.py',
                         'native\start-logon.ps1','native\settings.json',
                         'native\migration-complete.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $required))) {
        throw "Missing local installation file: $required"
    }
}
$userId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $scriptPath + '"') -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$trigger.Delay = 'PT15S'
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
# The task owns the display monitor for as long as the fullscreen window is open.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Start the existing Camo scanner and open the fullscreen display after Windows login.' -Force | Out-Null
Write-Host 'Login startup enabled. Current user login + 15 seconds; no Windows password saved.'
