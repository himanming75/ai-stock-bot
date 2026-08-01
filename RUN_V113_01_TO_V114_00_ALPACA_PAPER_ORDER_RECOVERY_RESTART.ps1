$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v114_00\output") {
    Remove-Item "release\v114_00\output" -Recurse -Force
}

Write-Host "=== V113.01-V114.00 INSTALL CHECK ==="
python tools/install_check_v113_01_to_v114_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V113.01-V114.00 REAL UNIT TESTS ==="
python -m unittest tools.test_alpaca_paper_order_recovery_v113_01_to_v114_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V113.01-V114.00 OFFLINE RECOVERY RESTART FIXTURE ==="
python tools/run_alpaca_paper_order_recovery_fixture_v113_01_to_v114_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V113.01-V114.00 VERIFY ==="
python tools/verify_alpaca_paper_order_recovery_v113_01_to_v114_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V113.01-V114.00 ALPACA PAPER ORDER RECOVERY RESTART PASS - READY TO COMMIT"
