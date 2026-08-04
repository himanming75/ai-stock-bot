param([string]$ProjectPath="C:\stock-bot")
$ErrorActionPreference="Stop"
$configPath=Join-Path $ProjectPath "release\v191_01_to_v195_64\config\production_scheduler_policy.json"
$config=Get-Content $configPath -Raw | ConvertFrom-Json

$jobs=@(
  @{Name="AI Stock Bot Pre Market";Job="pre_market";Enabled=$config.pre_market_enabled;At=$config.pre_market_time},
  @{Name="AI Stock Bot Market Health";Job="market_open_health";Enabled=$config.market_open_health_enabled;At=$config.market_open_health_time},
  @{Name="AI Stock Bot Qualification";Job="qualification_refresh";Enabled=$config.qualification_refresh_enabled;At=$config.qualification_refresh_time},
  @{Name="AI Stock Bot Portfolio Refresh";Job="portfolio_refresh";Enabled=$config.portfolio_refresh_enabled;At=$config.portfolio_refresh_time},
  @{Name="AI Stock Bot Post Market Report";Job="post_market_report";Enabled=$config.post_market_report_enabled;At=$config.post_market_report_time},
  @{Name="AI Stock Bot Nightly Backup";Job="nightly_backup";Enabled=$config.nightly_backup_enabled;At=$config.nightly_backup_time}
)

foreach($j in $jobs){
  if(-not $j.Enabled){continue}
  $script=Join-Path $ProjectPath "RUN_V191_PRODUCTION_JOB.ps1"
  $action=New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Job $($j.Job)"
  $trigger=New-ScheduledTaskTrigger -Daily -At $j.At
  $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 1)
  Register-ScheduledTask -TaskName $j.Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
  Write-Host "INSTALLED: $($j.Name) at $($j.At)"
}
Write-Host "PRODUCTION SCHEDULE INSTALL COMPLETE"
Write-Host "No scheduled task submits Paper or Live orders."
