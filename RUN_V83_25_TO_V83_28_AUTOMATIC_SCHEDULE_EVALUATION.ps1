
param(
    [switch]$CreateTrigger,
    [switch]$CompleteTrigger,
    [switch]$ClearTriggerLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.25-V83.28 AUTOMATIC SCHEDULE EVALUATION ==="
Write-Host "Local trigger planning only. No Windows Task or broker orders."

$argsList = @()
if ($CreateTrigger) {
    $argsList += "--create-trigger"
}
if ($CompleteTrigger) {
    $argsList += "--complete-trigger"
}
if ($ClearTriggerLock) {
    $argsList += "--clear-trigger-lock"
}
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_automatic_schedule_evaluation_v83_25_to_v83_28.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.25-V83.28 COMPLETE"
