
param(
    [switch]$ExecuteDispatch,
    [switch]$DryRun,
    [switch]$ClearDispatchLock
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.21-V83.24 SCHEDULED RUN DISPATCH ==="
Write-Host "One authorized Supervised Runner dispatch only. No broker orders."

$argsList = @()
if ($ExecuteDispatch) {
    $argsList += "--execute-dispatch"
}
if ($DryRun) {
    $argsList += "--dry-run"
}
if ($ClearDispatchLock) {
    $argsList += "--clear-dispatch-lock"
}

python tools/run_scheduled_run_dispatch_v83_21_to_v83_24.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.21-V83.24 COMPLETE"
