$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v125_00\output") {
    Remove-Item "release\v125_00\output" -Recurse -Force
}

Write-Host "=== V124.01-V125.00 INSTALL CHECK ==="
python tools/install_check_v124_01_to_v125_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V124.01-V125.00 REAL UNIT TESTS ==="
python -m unittest tools.test_broker_portfolio_reconciliation_v124_01_to_v125_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V124.01-V125.00 PORTFOLIO RECONCILIATION DEMO ==="
python tools/run_broker_portfolio_reconciliation_v124_01_to_v125_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V124.01-V125.00 VERIFY ==="
python tools/verify_broker_portfolio_reconciliation_v124_01_to_v125_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V124.01-V125.00 BROKER PORTFOLIO RECONCILIATION PASS - READY TO COMMIT"
