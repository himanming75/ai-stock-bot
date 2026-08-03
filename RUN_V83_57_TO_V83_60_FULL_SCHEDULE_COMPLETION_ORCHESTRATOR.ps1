param(
    [switch]$StartCycle,
    [switch]$FinalizeCycle,
    [switch]$ClearCycleLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.57-V83.60 FULL SCHEDULE COMPLETION ORCHESTRATOR ==="
Write-Host "Observation and certification only. No broker write."

$argsList = @()
if ($StartCycle) { $argsList += "--start-cycle" }
if ($FinalizeCycle) { $argsList += "--finalize-cycle" }
if ($ClearCycleLock) { $argsList += "--clear-cycle-lock" }
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_full_schedule_completion_orchestrator_v83_57_to_v83_60.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.57-V83.60 COMPLETE"
