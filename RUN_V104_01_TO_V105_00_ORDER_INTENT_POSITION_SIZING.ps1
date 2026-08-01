$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v105_00\output") {
    Remove-Item "release\v105_00\output" -Recurse -Force
}

Write-Host "=== V104.01-V105.00 INSTALL CHECK ==="
python tools/install_check_v104_01_to_v105_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V104.01-V105.00 REAL UNIT TESTS ==="
python -m unittest tools.test_order_intent_position_sizing_v104_01_to_v105_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V104.01-V105.00 ORDER INTENT DEMO ==="
python tools/run_order_intent_position_sizing_v104_01_to_v105_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V104.01-V105.00 VERIFY ==="
python tools/verify_order_intent_position_sizing_v104_01_to_v105_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V104.01-V105.00 REAL ORDER INTENT POSITION SIZING PASS - READY TO COMMIT"
