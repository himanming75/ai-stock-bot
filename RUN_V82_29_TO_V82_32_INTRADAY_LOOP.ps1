
param(
    [switch]$ExecuteLoop,
    [switch]$ResumeLoop
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.29-V82.32 INTRADAY PAPER LOOP MANAGER ==="
Write-Host "Single local loop only. No network or broker orders."

$argsList = @()
if ($ExecuteLoop) {
    $argsList += "--execute-loop"
}
if ($ResumeLoop) {
    $argsList += "--resume-loop"
}

python tools/run_intraday_loop_v82_29_to_v82_32.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.29-V82.32 COMPLETE"
