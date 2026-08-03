param(
    [switch]$Dispatch,
    [switch]$Execute,
    [switch]$ClearDispatchLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.29-V83.32 LOCAL TRIGGER DISPATCHER ==="
Write-Host "Dry run is default. Only V83.17 AuthorizeRun is whitelisted."
Write-Host "No broker orders and no external network writes."

$argsList = @()
if ($Dispatch) { $argsList += "--dispatch" }
if ($Execute) { $argsList += "--execute" }
if ($ClearDispatchLock) { $argsList += "--clear-dispatch-lock" }
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_local_trigger_dispatcher_v83_29_to_v83_32.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.29-V83.32 COMPLETE"
