$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$typed = Read-Host "Type REGISTER_AI_STOCK_BOT_AUTOSTART"
if($typed -ne "REGISTER_AI_STOCK_BOT_AUTOSTART"){throw "Confirmation phrase did not match."}
$taskName = "AIStockBot-AutonomousPaper"
$scriptPath = Join-Path $PSScriptRoot "RUN_V266_01_TO_V270_64_SUPERVISOR.ps1"
$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask `
  -TaskName $taskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "AI Stock Bot Autonomous Paper Session Supervisor" `
  -Force | Out-Null
$policyPath = ".\release\v266_01_to_v270_64\config\windows_autostart_recovery_policy.json"
$value = Get-Content $policyPath -Raw | ConvertFrom-Json
$value.autostart_registration_enabled = $true
$value | ConvertTo-Json -Depth 20 | Set-Content $policyPath -Encoding UTF8
Write-Host "Windows autostart task registered: $taskName"
