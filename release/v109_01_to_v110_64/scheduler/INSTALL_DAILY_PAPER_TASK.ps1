param(
    [string]$ProjectPath="C:\stock-bot",
    [string]$TaskName="AI Stock Bot Daily Paper Trading",
    [string]$StartTime="08:30"
)
$ErrorActionPreference="Stop"

$ScriptPath=Join-Path $ProjectPath "RUN_V109_01_TO_V110_64.ps1"
if(-not (Test-Path -LiteralPath $ScriptPath)){
    throw "RUN SCRIPT NOT FOUND: $ScriptPath"
}

$Action=New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""

$Trigger=New-ScheduledTaskTrigger -Daily -At $StartTime

$Settings=New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Runs AI Stock Bot autonomous paper operations. Live trading remains disabled." `
    -Force

Write-Host "TASK INSTALLED: $TaskName at $StartTime"
