$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v130_00\output") {
    Remove-Item "release\v130_00\output" -Recurse -Force
}
if (Test-Path "release\v130_00\ledger") {
    Remove-Item "release\v130_00\ledger" -Recurse -Force
}

Write-Host "=== V129.01-V130.00 INSTALL CHECK ==="
python tools/install_check_v129_01_to_v130_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V129.01-V130.00 REAL UNIT TESTS ==="
python -m unittest tools.test_existing_paper_order_lifecycle_monitor_v129_01_to_v130_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V129.01-V130.00 THREE-POLL MONITOR DEMO ==="
python tools/run_existing_paper_order_lifecycle_monitor_v129_01_to_v130_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V129.01-V130.00 VERIFY ==="
python tools/verify_existing_paper_order_lifecycle_monitor_v129_01_to_v130_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V129.01-V130.00 EXISTING PAPER ORDER LIFECYCLE MONITOR PASS - READY TO COMMIT"
