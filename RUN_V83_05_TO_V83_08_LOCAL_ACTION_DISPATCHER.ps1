
param(
    [switch]$ExecuteAction,
    [switch]$DryRun,
    [switch]$ClearDispatchLock
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.05-V83.08 LOCAL ACTION DISPATCHER ==="
Write-Host "Allowlisted local commands only. No broker orders."

$argsList = @()
if ($ExecuteAction) {
    $argsList += "--execute-action"
}
if ($DryRun) {
    $argsList += "--dry-run"
}
if ($ClearDispatchLock) {
    $argsList += "--clear-dispatch-lock"
}

python tools/run_local_action_dispatcher_v83_05_to_v83_08.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.05-V83.08 COMPLETE"
