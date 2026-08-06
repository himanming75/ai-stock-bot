[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_v12001_to_v13000_portfolio_context -v
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

python .\tools\run_v12001_to_v13000_portfolio_context.py *> $null
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

$tempVerify = Join-Path $env:TEMP "verify_v12001_to_v13000.py"

$pythonCode = @"
import json
from pathlib import Path

path = Path(r"release/v12001_13000_portfolio_context/portfolio_context_certification.json")
data = json.loads(path.read_text(encoding="utf-8-sig"))

assert data["status"] == "PASS"
assert data["actual_broker_write_performed"] is False
assert data["actual_position_allocation_performed"] is False
assert data["actual_model_weight_update_performed"] is False
assert data["actual_live_learning_performed"] is False
assert data["actual_order_submission_performed"] is False
assert data["actual_order_cancel_performed"] is False
assert data["actual_paper_orders_submitted"] == 0
assert data["actual_live_orders_submitted"] == 0
"@

[System.IO.File]::WriteAllText(
    $tempVerify,
    $pythonCode,
    (New-Object System.Text.UTF8Encoding($false))
)

python $tempVerify
$verifyExitCode = $LASTEXITCODE

Remove-Item $tempVerify -Force -ErrorAction SilentlyContinue

if($verifyExitCode -ne 0){ exit $verifyExitCode }

Write-Host "VERIFY: PASS"
Write-Host "CERTIFICATION: PASS"
Write-Host "ZERO ACTION CONTRACT: PASS"
