param(
    [switch]$RecoverTrigger,
    [switch]$ClearRecoveryLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.33-V83.36 TRIGGER RECOVERY & DISPATCH CHAIN ==="
Write-Host "State aggregation and supervised recovery only."
Write-Host "No broker orders, no network writes, and no automatic dispatch."

$argsList = @()
if ($RecoverTrigger) { $argsList += "--recover-trigger" }
if ($ClearRecoveryLock) { $argsList += "--clear-recovery-lock" }
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_trigger_recovery_dispatch_chain_v83_33_to_v83_36.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.33-V83.36 COMPLETE"
