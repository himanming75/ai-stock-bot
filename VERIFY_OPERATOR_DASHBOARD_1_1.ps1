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

& $Python -m unittest tools.test_operator_dashboard_1_1 -v
if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$tempVerify = Join-Path $env:TEMP "verify_operator_dashboard_1_1.py"
$ProjectRoot = (Get-Location).Path

$pythonCode = @"
import sys
from pathlib import Path

root = Path(r"$ProjectRoot")
sys.path.insert(0, str(root))

from operator_dashboard import create_app

app = create_app(root)
health = app.health_payload()
status = app.status_payload()

assert health["status"] == "PASS"
assert health["dashboard"] == "OPERATOR_DASHBOARD_1_1"
assert health["live_write_enabled"] is False
assert "operation_console" in status
assert status["safety"]["live_write_enabled"] is False
assert status["safety"]["multi_account_enabled"] is False
"@

[System.IO.File]::WriteAllText(
    $tempVerify,
    $pythonCode,
    (New-Object System.Text.UTF8Encoding($false))
)

& $Python $tempVerify
$ExitCode = $LASTEXITCODE
Remove-Item $tempVerify -Force -ErrorAction SilentlyContinue

if($ExitCode -ne 0) {
    exit $ExitCode
}

Write-Host "VERIFY: PASS"
Write-Host "OPERATOR DASHBOARD 1.1: READY"
Write-Host "OPERATION CONSOLE: READY"
Write-Host "ETRADE LIVE WRITE: OFF"
