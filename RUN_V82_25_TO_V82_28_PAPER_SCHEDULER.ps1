
param(
    [switch]$WriteHeartbeat,
    [switch]$AuthorizeTick,
    [switch]$CompleteTick
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.25-V82.28 PAPER TRADING SCHEDULER ==="
Write-Host "Local tick scheduling only. No network or broker orders."

$argsList = @()
if ($WriteHeartbeat) {
    $argsList += "--write-heartbeat"
}
if ($AuthorizeTick) {
    $argsList += "--authorize-tick"
}
if ($CompleteTick) {
    $argsList += "--complete-tick"
}

python tools/run_paper_scheduler_v82_25_to_v82_28.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.25-V82.28 COMPLETE"
