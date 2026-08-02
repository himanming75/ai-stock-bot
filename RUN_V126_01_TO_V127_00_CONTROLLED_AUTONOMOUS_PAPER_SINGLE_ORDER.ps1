$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v127_00\output") {
    Remove-Item "release\v127_00\output" -Recurse -Force
}

Write-Host "=== V126.01-V127.00 INSTALL CHECK ==="
python tools/install_check_v126_01_to_v127_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V126.01-V127.00 REAL UNIT TESTS ==="
python -m unittest tools.test_controlled_autonomous_paper_single_order_v126_01_to_v127_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V126.01-V127.00 EXISTING ORDER GUARD DEMO ==="
python tools/run_controlled_autonomous_paper_single_order_v126_01_to_v127_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V126.01-V127.00 VERIFY ==="
python tools/verify_controlled_autonomous_paper_single_order_v126_01_to_v127_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V126.01-V127.00 CONTROLLED AUTONOMOUS PAPER SINGLE ORDER PASS - READY TO COMMIT"
