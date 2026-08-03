
param(
    [switch]$StartSession,
    [switch]$EndSession,
    [switch]$RecoverSession
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.21-V82.24 PAPER TRADING SESSION MANAGER ==="
Write-Host "Local session state only. No network or broker orders."

$argsList = @()
if ($StartSession) {
    $argsList += "--start-session"
}
if ($EndSession) {
    $argsList += "--end-session"
}
if ($RecoverSession) {
    $argsList += "--recover-session"
}

python tools/run_paper_session_manager_v82_21_to_v82_24.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.21-V82.24 COMPLETE"
