param(
    [switch]$AuthorizeAutonomousCycle,
    [switch]$CompleteCycle,
    [switch]$ClearAutonomousLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.73-V83.76 PAPER AUTONOMOUS MODE ==="
Write-Host "Single paper cycle only. No continuous loop or broker write."

$argsList = @()
if ($AuthorizeAutonomousCycle) {
    $argsList += "--authorize-autonomous-cycle"
}
if ($CompleteCycle) {
    $argsList += "--complete-cycle"
}
if ($ClearAutonomousLock) {
    $argsList += "--clear-autonomous-lock"
}
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_paper_autonomous_mode_v83_73_to_v83_76.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.73-V83.76 COMPLETE"
