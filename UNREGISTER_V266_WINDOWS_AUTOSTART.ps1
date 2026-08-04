$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$taskName = "AIStockBot-AutonomousPaper"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
$policyPath = ".\release\v266_01_to_v270_64\config\windows_autostart_recovery_policy.json"
$value = Get-Content $policyPath -Raw | ConvertFrom-Json
$value.autostart_registration_enabled = $false
$value | ConvertTo-Json -Depth 20 | Set-Content $policyPath -Encoding UTF8
Write-Host "Windows autostart task removed."
