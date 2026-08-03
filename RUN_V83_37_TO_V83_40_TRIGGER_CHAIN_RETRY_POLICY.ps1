param(
    [switch]$PlanRetry,
    [switch]$CompleteRetry,
    [switch]$ClearRetryLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.37-V83.40 TRIGGER CHAIN RETRY POLICY ==="
Write-Host "Retry planning only. No automatic retry execution."
Write-Host "No broker orders and no external network writes."

$argsList = @()
if ($PlanRetry) { $argsList += "--plan-retry" }
if ($CompleteRetry) { $argsList += "--complete-retry" }
if ($ClearRetryLock) { $argsList += "--clear-retry-lock" }
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_trigger_chain_retry_policy_v83_37_to_v83_40.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.37-V83.40 COMPLETE"
