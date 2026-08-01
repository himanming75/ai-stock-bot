$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v112_00\output") {
    Remove-Item "release\v112_00\output" -Recurse -Force
}

Write-Host "=== V111.01-V112.00 INSTALL CHECK ==="
python tools/install_check_v111_01_to_v112_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V111.01-V112.00 REAL UNIT TESTS ==="
python -m unittest tools.test_controlled_alpaca_paper_order_optin_v111_01_to_v112_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V111.01-V112.00 OFFLINE SINGLE-ORDER FIXTURE ==="
python tools/run_controlled_alpaca_paper_order_fixture_v111_01_to_v112_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V111.01-V112.00 VERIFY ==="
python tools/verify_controlled_alpaca_paper_order_optin_v111_01_to_v112_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V111.01-V112.00 CONTROLLED ALPACA PAPER ORDER OPT-IN PASS - READY TO COMMIT"
