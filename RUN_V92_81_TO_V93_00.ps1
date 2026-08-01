$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v93_00\output"){Remove-Item "release\v93_00\output" -Recurse -Force}
Write-Host "=== V92.81-V93.00 INSTALL CHECK ==="
python tools/install_check_v92_81_to_v93_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.81-V93.00 TESTS ==="
python -m unittest tools.test_actual_paper_submission_release_candidate_v92_81_to_v93_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.81-V93.00 PIPELINE ==="
python tools/run_v92_81_to_v93_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.81-V93.00 VERIFY ==="
python tools/verify_v92_81_to_v93_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V92.81-V93.00 PASS - READY TO COMMIT"
