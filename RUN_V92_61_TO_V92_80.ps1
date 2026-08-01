$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v92_80\output"){Remove-Item "release\v92_80\output" -Recurse -Force}
Write-Host "=== V92.61-V92.80 INSTALL CHECK ==="
python tools/install_check_v92_61_to_v92_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.61-V92.80 TESTS ==="
python -m unittest tools.test_actual_paper_e2e_submission_certification_v92_61_to_v92_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.61-V92.80 PIPELINE ==="
python tools/run_v92_61_to_v92_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.61-V92.80 VERIFY ==="
python tools/verify_v92_61_to_v92_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V92.61-V92.80 PASS - READY TO COMMIT"
