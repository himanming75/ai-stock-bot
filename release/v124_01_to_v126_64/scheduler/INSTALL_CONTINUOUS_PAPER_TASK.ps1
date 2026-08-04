param(
[string]$ProjectPath="C:\stock-bot",
[string]$TaskName="AI Stock Bot Real Paper Shadow",
[string]$StartTime="06:25"
)
$ErrorActionPreference="Stop"
$script=Join-Path $ProjectPath "RUN_V124_TO_V126_REAL_SHADOW.ps1"
$action=New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$script`""
$trigger=New-ScheduledTaskTrigger -Daily -At $StartTime
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "READ-ONLY SHADOW TASK INSTALLED: $TaskName"
