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

& $Python -m unittest tools.test_market_open_auto_validation -v
if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$tempVerify = Join-Path $env:TEMP "verify_market_open_auto_validation.py"
$ProjectRoot = (Get-Location).Path

$pythonCode = @"
import sys
from pathlib import Path

root = Path(r"$ProjectRoot")
sys.path.insert(0, str(root))

from market_open_validation.runner import AutoValidationRunner

runner = AutoValidationRunner(root, dry_run=True)
state = runner._state("VERIFY")

assert state["paper_broker"] == "ALPACA"
assert state["live_broker"] == "ETRADE"
assert state["paper_only"] is True
assert state["etrade_live_write_enabled"] is False
assert state["live_orders_submitted"] == 0
assert state["maximum_validation_orders"] == 1
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
Write-Host "MARKET OPEN WATCHER: READY"
Write-Host "ONE PAPER VALIDATION ORDER CONTRACT: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
