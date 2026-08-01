$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v110_00\output") {
    Remove-Item "release\v110_00\output" -Recurse -Force
}

Write-Host "=== V109.01-V110.00 INSTALL CHECK ==="
python tools/install_check_v109_01_to_v110_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V109.01-V110.00 REAL UNIT TESTS ==="
python -m unittest tools.test_alpaca_paper_broker_integration_v109_01_to_v110_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V109.01-V110.00 SAFE OFFLINE BROKER DEMO ==="
python tools/run_alpaca_paper_broker_integration_v109_01_to_v110_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V109.01-V110.00 VERIFY ==="
python tools/verify_alpaca_paper_broker_integration_v109_01_to_v110_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V109.01-V110.00 REAL ALPACA PAPER BROKER INTEGRATION FOUNDATION PASS - READY TO COMMIT"
