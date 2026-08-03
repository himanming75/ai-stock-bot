param(
    [switch]$Analyze,
    [switch]$ApplyRecovery,
    [switch]$ClearStaleLocks,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.61-V83.64 CRASH RECOVERY & RESTART ==="
Write-Host "Supervised local recovery only. No broker write."

$argsList = @()
if ($Analyze) { $argsList += "--analyze" }
if ($ApplyRecovery) { $argsList += "--apply-recovery" }
if ($ClearStaleLocks) { $argsList += "--clear-stale-locks" }
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_crash_recovery_restart_continuation_v83_61_to_v83_64.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.61-V83.64 COMPLETE"
