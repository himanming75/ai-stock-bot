$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$path = ".\release\v266_01_to_v270_64\config\windows_autostart_recovery_policy.json"
$value = Get-Content $path -Raw | ConvertFrom-Json
$value.supervisor_enabled = $false
$value | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8
Write-Host "Windows Supervisor disabled."
