$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v107_00\output") {
    Remove-Item "release\v107_00\output" -Recurse -Force
}

Write-Host "=== V106.01-V107.00 INSTALL CHECK ==="
python tools/install_check_v106_01_to_v107_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V106.01-V107.00 REAL UNIT TESTS ==="
python -m unittest tools.test_portfolio_fill_accounting_v106_01_to_v107_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V106.01-V107.00 PORTFOLIO ACCOUNTING DEMO ==="
python tools/run_portfolio_fill_accounting_v106_01_to_v107_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V106.01-V107.00 VERIFY ==="
python tools/verify_portfolio_fill_accounting_v106_01_to_v107_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V106.01-V107.00 REAL PORTFOLIO FILL ACCOUNTING PASS - READY TO COMMIT"
