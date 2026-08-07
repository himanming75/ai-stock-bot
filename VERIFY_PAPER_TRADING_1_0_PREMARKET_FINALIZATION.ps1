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
    tools.test_paper_trading_1_0_premarket_finalization `
    -v

if($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$tempVerify = Join-Path $env:TEMP "verify_paper_premarket_finalization.py"

$pythonCode = @"
import json
from pathlib import Path

path = Path(r"release/paper_trading_1_0_premarket_finalization/premarket_finalization_result.json")
data = json.loads(path.read_text(encoding="utf-8-sig"))

assert data["scope_locked"] is True
assert data["new_feature_development_allowed"] is False
assert data["actual_market_day_validation_performed"] is False
assert data["actual_paper_orders_submitted"] == 0
assert data["actual_live_orders_submitted"] == 0
assert len(data["tomorrow_only_remaining"]) == 4
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
Write-Host "SCOPE LOCK: PASS"
Write-Host "ZERO ORDER CONTRACT: PASS"
Write-Host "TOMORROW VALIDATION SEPARATION: PASS"
