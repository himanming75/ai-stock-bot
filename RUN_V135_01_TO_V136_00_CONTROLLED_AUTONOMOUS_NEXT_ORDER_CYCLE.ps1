$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v136_00\output"){Remove-Item "release\v136_00\output" -Recurse -Force}
if(Test-Path "release\v136_00\cycle"){Remove-Item "release\v136_00\cycle" -Recurse -Force}

Write-Host "=== V135.01-V136.00 INSTALL CHECK ==="
python tools/install_check_v135_01_to_v136_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V135.01-V136.00 REAL UNIT TESTS ==="
python -m unittest tools.test_controlled_autonomous_next_order_cycle_v135_01_to_v136_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V135.01-V136.00 NEXT ORDER CYCLE DEMO ==="
python tools/run_controlled_autonomous_next_order_cycle_v135_01_to_v136_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V135.01-V136.00 VERIFY ==="
python tools/verify_controlled_autonomous_next_order_cycle_v135_01_to_v136_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V135.01-V136.00 CONTROLLED AUTONOMOUS NEXT ORDER CYCLE PASS - READY TO COMMIT"
