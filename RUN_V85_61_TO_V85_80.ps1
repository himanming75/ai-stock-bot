$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v85_80\output"){Remove-Item "release\v85_80\output" -Recurse -Force}
Write-Host "=== V85.61-V85.80 INSTALL CHECK ==="
python tools/install_check_v85_61_to_v85_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.61-V85.80 TESTS ==="
python -m unittest tools.test_paper_order_submission_sim_v85_61_to_v85_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.61-V85.80 PIPELINE ==="
python tools/run_v85_61_to_v85_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.61-V85.80 VERIFY ==="
python tools/verify_v85_61_to_v85_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V85.61-V85.80 PASS - READY TO COMMIT"
