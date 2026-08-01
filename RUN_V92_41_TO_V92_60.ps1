$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v92_60\output"){Remove-Item "release\v92_60\output" -Recurse -Force}
Write-Host "=== V92.41-V92.60 INSTALL CHECK ==="
python tools/install_check_v92_41_to_v92_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.41-V92.60 TESTS ==="
python -m unittest tools.test_actual_paper_final_submission_certification_v92_41_to_v92_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.41-V92.60 PIPELINE ==="
python tools/run_v92_41_to_v92_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.41-V92.60 VERIFY ==="
python tools/verify_v92_41_to_v92_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V92.41-V92.60 PASS - READY TO COMMIT"
