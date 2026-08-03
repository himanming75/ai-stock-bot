
param(
    [switch]$ExecuteCycle,
    [switch]$ResumeCycle,
    [switch]$ClearCycleLock
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.09-V83.12 CONTROLLED AUTOMATION CYCLE ==="
Write-Host "Single controlled cycle only. No broker orders."

$argsList = @()
if ($ExecuteCycle) {
    $argsList += "--execute-cycle"
}
if ($ResumeCycle) {
    $argsList += "--resume-cycle"
}
if ($ClearCycleLock) {
    $argsList += "--clear-cycle-lock"
}

python tools/run_controlled_automation_cycle_v83_09_to_v83_12.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V83.09-V83.12 COMPLETE"
