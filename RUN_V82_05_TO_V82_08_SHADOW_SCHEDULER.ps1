
param(
    [switch]$WriteHeartbeat,
    [switch]$AuthorizeNextCycle
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.05-V82.08 AUTONOMOUS SHADOW SCHEDULER ==="
Write-Host "Local scheduling state only. No network or broker orders."

$argsList = @()
if ($WriteHeartbeat) {
    $argsList += "--write-heartbeat"
}
if ($AuthorizeNextCycle) {
    $argsList += "--authorize-next-cycle"
}

python tools/run_shadow_scheduler_v82_05_to_v82_08.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.05-V82.08 COMPLETE"
