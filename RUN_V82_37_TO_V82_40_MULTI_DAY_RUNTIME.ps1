
param(
    [switch]$ExecuteRollover,
    [switch]$ResetRuntime
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.37-V82.40 MULTI-DAY PAPER RUNTIME ==="
Write-Host "Local rollover planning only. No broker orders."

$argsList = @()
if ($ExecuteRollover) {
    $argsList += "--execute-rollover"
}
if ($ResetRuntime) {
    $argsList += "--reset-runtime"
}

python tools/run_multi_day_runtime_v82_37_to_v82_40.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.37-V82.40 COMPLETE"
