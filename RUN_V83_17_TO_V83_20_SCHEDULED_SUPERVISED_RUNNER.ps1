
param(
    [switch]$AuthorizeRun,
    [switch]$CompleteRun,
    [switch]$ClearScheduleLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.17-V83.20 SCHEDULED SUPERVISED RUNNER ==="
Write-Host "Schedule gate and authorization only. No broker orders."

$argsList = @()
if ($AuthorizeRun) {
    $argsList += "--authorize-run"
}
if ($CompleteRun) {
    $argsList += "--complete-run"
}
if ($ClearScheduleLock) {
    $argsList += "--clear-schedule-lock"
}
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_scheduled_supervised_runner_v83_17_to_v83_20.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.17-V83.20 COMPLETE"
