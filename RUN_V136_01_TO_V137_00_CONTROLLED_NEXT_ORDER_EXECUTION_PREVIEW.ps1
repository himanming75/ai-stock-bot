$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v137_00\output"){Remove-Item "release\v137_00\output" -Recurse -Force}
if(Test-Path "release\v137_00\preview"){Remove-Item "release\v137_00\preview" -Recurse -Force}

Write-Host "=== V136.01-V137.00 INSTALL CHECK ==="
python tools/install_check_v136_01_to_v137_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V136.01-V137.00 REAL UNIT TESTS ==="
python -m unittest tools.test_controlled_next_order_execution_preview_v136_01_to_v137_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V136.01-V137.00 EXECUTION PREVIEW DEMO ==="
python tools/run_controlled_next_order_execution_preview_v136_01_to_v137_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V136.01-V137.00 VERIFY ==="
python tools/verify_controlled_next_order_execution_preview_v136_01_to_v137_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V136.01-V137.00 CONTROLLED NEXT ORDER EXECUTION PREVIEW PASS - READY TO COMMIT"
