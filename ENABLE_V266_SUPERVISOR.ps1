$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$path = ".\release\v266_01_to_v270_64\config\windows_autostart_recovery_policy.json"
$typed = Read-Host "Type ENABLE_WINDOWS_SUPERVISOR"
if($typed -ne "ENABLE_WINDOWS_SUPERVISOR"){throw "Confirmation phrase did not match."}
$value = Get-Content $path -Raw | ConvertFrom-Json
$value.supervisor_enabled = $true
$value | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8
Write-Host "Windows Supervisor enabled."
