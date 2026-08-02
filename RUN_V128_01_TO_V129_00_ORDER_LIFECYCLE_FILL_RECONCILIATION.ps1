$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v129_00\output") {
    Remove-Item "release\v129_00\output" -Recurse -Force
}

Write-Host "=== V128.01-V129.00 INSTALL CHECK ==="
python tools/install_check_v128_01_to_v129_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V128.01-V129.00 REAL UNIT TESTS ==="
python -m unittest tools.test_actual_order_lifecycle_fill_reconciliation_v128_01_to_v129_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V128.01-V129.00 LIFECYCLE/FILL GATE ==="
python tools/run_order_lifecycle_fill_reconciliation_v128_01_to_v129_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V128.01-V129.00 VERIFY ==="
python tools/verify_order_lifecycle_fill_reconciliation_v128_01_to_v129_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V128.01-V129.00 ORDER LIFECYCLE FILL RECONCILIATION PASS - READY TO COMMIT"
