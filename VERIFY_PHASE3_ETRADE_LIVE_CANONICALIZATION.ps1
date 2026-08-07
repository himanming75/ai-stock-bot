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

& $Python -m unittest `
    tools.test_phase3_etrade_live_canonicalization `
    -v

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$tempVerify = Join-Path $env:TEMP "verify_phase3_etrade_live.py"

$pythonCode = @"
import json
from pathlib import Path

path = Path(r"release/phase3_etrade_live_canonicalization/phase3_etrade_live_result.json")
data = json.loads(path.read_text(encoding="utf-8-sig"))

assert data["scope_locked"] is True
assert data["paper_broker"] == "ALPACA"
assert data["live_broker"] == "ETRADE"
assert data["other_brokers_enabled"] is False
assert data["etrade_live_submission_enabled"] is False
assert data["etrade_live_cancel_enabled"] is False
assert data["etrade_live_allocation_enabled"] is False
assert data["actual_live_orders_submitted"] == 0
assert data["actual_live_orders_cancelled"] == 0
assert len(data["selected_paths"]) == 14
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
Write-Host "BROKER ROLE LOCK: PASS"
Write-Host "ETRADE LIVE WRITE LOCK: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
