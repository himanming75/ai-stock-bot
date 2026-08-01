$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v113_00\output") {
    Remove-Item "release\v113_00\output" -Recurse -Force
}

Write-Host "=== V112.01-V113.00 INSTALL CHECK ==="
python tools/install_check_v112_01_to_v113_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V112.01-V113.00 REAL UNIT TESTS ==="
python -m unittest tools.test_actual_alpaca_paper_order_validation_v112_01_to_v113_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V112.01-V113.00 OFFLINE ORDER VALIDATION FIXTURE ==="
python tools/run_actual_alpaca_paper_order_validation_fixture_v112_01_to_v113_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V112.01-V113.00 VERIFY ==="
python tools/verify_actual_alpaca_paper_order_validation_v112_01_to_v113_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V112.01-V113.00 ACTUAL ALPACA PAPER ORDER VALIDATION PASS - READY TO COMMIT"
