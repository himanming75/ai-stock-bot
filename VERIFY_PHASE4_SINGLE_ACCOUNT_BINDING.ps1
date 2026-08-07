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
    tools.test_phase4_single_account_binding `
    -v

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$tempVerify = Join-Path $env:TEMP "verify_phase4_single_account.py"

$pythonCode = @"
import json
from pathlib import Path

path = Path(r"release/phase4_single_account_binding/phase4_single_account_result.json")
data = json.loads(path.read_text(encoding="utf-8-sig"))

assert data["scope_locked"] is True
assert data["multi_account_enabled"] is False
assert data["alpaca_role"] == "PAPER_ONLY_SINGLE_ACCOUNT"
assert data["etrade_role"] == "LIVE_ONLY_SINGLE_ACCOUNT"
assert data["runtime_account_switch_enabled"] is False
assert data["automatic_account_discovery_enabled"] is False
assert data["live_submission_enabled"] is False
assert data["actual_paper_orders_submitted"] == 0
assert data["actual_live_orders_submitted"] == 0
assert len(data["selected_paths"]) == 12
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
Write-Host "SINGLE ACCOUNT ROLE LOCK: PASS"
Write-Host "ACCOUNT SWITCH OFF: PASS"
Write-Host "ZERO ORDER CONTRACT: PASS"
