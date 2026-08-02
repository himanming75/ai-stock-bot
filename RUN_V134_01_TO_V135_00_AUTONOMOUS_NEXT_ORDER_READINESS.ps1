$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v135_00\output"){Remove-Item "release\v135_00\output" -Recurse -Force}
if(Test-Path "release\v135_00\readiness"){Remove-Item "release\v135_00\readiness" -Recurse -Force}

Write-Host "=== V134.01-V135.00 INSTALL CHECK ==="
python tools/install_check_v134_01_to_v135_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V134.01-V135.00 REAL UNIT TESTS ==="
python -m unittest tools.test_autonomous_next_order_readiness_v134_01_to_v135_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V134.01-V135.00 NEXT ORDER READINESS DEMO ==="
python tools/run_autonomous_next_order_readiness_v134_01_to_v135_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V134.01-V135.00 VERIFY ==="
python tools/verify_autonomous_next_order_readiness_v134_01_to_v135_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V134.01-V135.00 AUTONOMOUS NEXT ORDER READINESS PASS - READY TO COMMIT"
