$ErrorActionPreference = 'Stop'
$nativeRoot = Join-Path $PSScriptRoot 'native'
Set-Content -LiteralPath (Join-Path $nativeRoot 'stop.request') -Value 'stop'
Write-Host 'Requested local platform shutdown. Database will be stopped safely.'
