$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v84_80\output"){Remove-Item "release\v84_80\output" -Recurse -Force}
Write-Host "=== V84.61-V84.80 INSTALL CHECK ==="
python tools/install_check_v84_61_to_v84_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.61-V84.80 TESTS ==="
python -m unittest tools.test_live_order_submission_sim_v84_61_to_v84_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.61-V84.80 PIPELINE ==="
python tools/run_v84_61_to_v84_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.61-V84.80 VERIFY ==="
python tools/verify_v84_61_to_v84_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V84.61-V84.80 PASS - READY TO COMMIT"
