$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v123_00\output") {
    Remove-Item "release\v123_00\output" -Recurse -Force
}

Write-Host "=== V122.01-V123.00 INSTALL CHECK ==="
python tools/install_check_v122_01_to_v123_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V122.01-V123.00 REAL UNIT TESTS ==="
python -m unittest tools.test_autonomous_paper_order_identity_reconciliation_v122_01_to_v123_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V122.01-V123.00 ORDER IDENTITY DEMO ==="
python tools/run_autonomous_paper_order_identity_reconciliation_v122_01_to_v123_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V122.01-V123.00 VERIFY ==="
python tools/verify_autonomous_paper_order_identity_reconciliation_v122_01_to_v123_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V122.01-V123.00 AUTONOMOUS PAPER ORDER IDENTITY RECONCILIATION PASS - READY TO COMMIT"
