[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if(Test-Path ".\.venv\Scripts\python.exe") {
    $Python = ".\.venv\Scripts\python.exe"
}
else {
    $Python = "python"
}

& $Python -m unittest tools.test_operator_dashboard -v
if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$tempVerify = Join-Path $env:TEMP "verify_operator_dashboard.py"
$ProjectRoot = (Get-Location).Path

$pythonCode = @"
import sys
from pathlib import Path

project_root = Path(r"$ProjectRoot")
sys.path.insert(0, str(project_root))

from operator_dashboard import create_app

app = create_app(project_root)
health = app.health_payload()
status = app.status_payload()

assert health["status"] == "PASS"
assert health["paper_broker"] == "ALPACA"
assert health["live_broker"] == "ETRADE"
assert health["live_write_enabled"] is False

assert status["safety"]["paper_broker"] == "ALPACA"
assert status["safety"]["live_broker"] == "ETRADE"
assert status["safety"]["live_write_enabled"] is False
assert status["safety"]["live_cancel_enabled"] is False
assert status["safety"]["live_allocation_enabled"] is False
assert status["safety"]["multi_account_enabled"] is False
assert status["safety"]["runtime_account_switch_enabled"] is False
"@

[System.IO.File]::WriteAllText(
    $tempVerify,
    $pythonCode,
    (New-Object System.Text.UTF8Encoding($false))
)

& $Python $tempVerify
$ExitCode = $LASTEXITCODE

Remove-Item `
    $tempVerify `
    -Force `
    -ErrorAction SilentlyContinue

if($ExitCode -ne 0) {
    exit $ExitCode
}

Write-Host "VERIFY: PASS"
Write-Host "OPERATOR DASHBOARD: READY"
Write-Host "ALPACA PAPER CONTROL: READY"
Write-Host "ETRADE LIVE WRITE: OFF"