param(
[string]$ProjectPath="C:\stock-bot",
[string]$WebTaskName="AI Stock Bot Web Controller",
[string]$PreMarketTaskName="AI Stock Bot Pre Market",
[string]$ShadowTaskName="AI Stock Bot Paper Shadow",
[string]$PostMarketTaskName="AI Stock Bot Post Market"
)
$ErrorActionPreference="Stop"
$configPath=Join-Path $ProjectPath "release\v156_01_to_v160_64\config\operations_manager.json"
$config=Get-Content $configPath -Raw | ConvertFrom-Json

function Register-SafeTask($Name,$Script,$At,$AtLogon=$false){
  $action=New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
  if($AtLogon){$trigger=New-ScheduledTaskTrigger -AtLogOn}
  else{$trigger=New-ScheduledTaskTrigger -Daily -At $At}
  $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
  Write-Host "INSTALLED: $Name"
}

if($config.web_controller_autostart_enabled){
 Register-SafeTask $WebTaskName (Join-Path $ProjectPath "RUN_V141_01_TO_V145_64_WEB_CONTROLLER.ps1") $null $true
}
if($config.pre_market_check_enabled){
 Register-SafeTask $PreMarketTaskName (Join-Path $ProjectPath "RUN_V156_PRE_MARKET_JOB.ps1") $config.pre_market_time
}
if($config.intraday_shadow_enabled){
 Register-SafeTask $ShadowTaskName (Join-Path $ProjectPath "RUN_V156_INTRADAY_SHADOW_JOB.ps1") $config.intraday_time
}
if($config.post_market_report_enabled){
 Register-SafeTask $PostMarketTaskName (Join-Path $ProjectPath "RUN_V156_POST_MARKET_JOB.ps1") $config.post_market_time
}
Write-Host "SAFE SCHEDULE INSTALL COMPLETE"
Write-Host "No scheduled task can submit a Paper or Live order."
