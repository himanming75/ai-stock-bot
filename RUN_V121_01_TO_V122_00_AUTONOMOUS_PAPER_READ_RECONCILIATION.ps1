$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v122_00\output") {
    Remove-Item "release\v122_00\output" -Recurse -Force
}

Write-Host "=== V121.01-V122.00 INSTALL CHECK ==="
python tools/install_check_v121_01_to_v122_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V121.01-V122.00 REAL UNIT TESTS ==="
python -m unittest tools.test_autonomous_paper_read_reconciliation_v121_01_to_v122_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V121.01-V122.00 RECONCILIATION DEMO ==="
python tools/run_autonomous_paper_read_reconciliation_v121_01_to_v122_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V121.01-V122.00 VERIFY ==="
python tools/verify_autonomous_paper_read_reconciliation_v121_01_to_v122_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V121.01-V122.00 AUTONOMOUS PAPER READ RECONCILIATION PASS - READY TO COMMIT"
