param(
    [switch]$Execute,
    [switch]$RunLocal,
    [switch]$ClearRunnerLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.49-V83.52 SUPERVISED RE-ENTRY RUNNER ==="
Write-Host "Dry run is default. No broker or network write."

$argsList = @()
if ($Execute) { $argsList += "--execute" }
if ($RunLocal) { $argsList += "--run-local" }
if ($ClearRunnerLock) { $argsList += "--clear-runner-lock" }
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_supervised_reentry_runner_v83_49_to_v83_52.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.49-V83.52 COMPLETE"
