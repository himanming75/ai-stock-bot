$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v92_00\output"){Remove-Item "release\v92_00\output" -Recurse -Force}
Write-Host "=== V91.81-V92.00 INSTALL CHECK ==="
python tools/install_check_v91_81_to_v92_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.81-V92.00 TESTS ==="
python -m unittest tools.test_actual_paper_order_submission_optin_v91_81_to_v92_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.81-V92.00 PIPELINE ==="
python tools/run_v91_81_to_v92_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.81-V92.00 VERIFY ==="
python tools/verify_v91_81_to_v92_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V91.81-V92.00 PASS - READY TO COMMIT"
