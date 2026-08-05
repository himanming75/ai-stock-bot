param(
    [string]$TaskName="AI Stock Bot Daily Session",
    [string]$RepositoryRoot="C:\stock-bot"
)

$ErrorActionPreference="Stop"

$ScriptPath=Join-Path `
    $RepositoryRoot `
    "RUN_DAILY_SESSION_MANAGER_AND_WATCHDOG.ps1"

if(-not(Test-Path -LiteralPath $ScriptPath)){
    throw "Daily Session script not found: $ScriptPath"
}

$PowerShellExe=(
    Get-Command powershell.exe
).Source

$Argument=(
    "-NoProfile -ExecutionPolicy Bypass " +
    "-File `"$ScriptPath`""
)

$Action=New-ScheduledTaskAction `
    -Execute $PowerShellExe `
    -Argument $Argument `
    -WorkingDirectory $RepositoryRoot

$Trigger=New-ScheduledTaskTrigger -AtLogOn

$Settings=New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 12)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Starts the AI Stock Bot Daily Session Manager in read-only Paper mode after Windows logon." `
    -Force

Write-Host "STARTUP TASK REGISTERED"
Write-Host "Task Name: $TaskName"
Write-Host "Mode: READ-ONLY PAPER AUTOMATION"
Write-Host "ORDER SUBMISSION: OFF"
