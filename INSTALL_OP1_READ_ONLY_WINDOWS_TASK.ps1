param(
    [string]$TaskName = "AIStockBot-ReadOnly-Collector",
    [int]$IntervalMinutes = 15
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($IntervalMinutes -lt 5) {
    throw "IntervalMinutes must be at least 5."
}

$collectorScript = Join-Path $PSScriptRoot "RUN_OP1_13_TO_OP1_16_SNAPSHOT_COLLECTOR.ps1"
if (-not (Test-Path $collectorScript)) {
    throw "Collector script not found: $collectorScript"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$collectorScript`" -EnableNetwork"

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "AI Stock Bot Alpaca Paper GET-only snapshot collector. No order submission." `
    -Force

Write-Host "TASK_INSTALLED=$TaskName"
