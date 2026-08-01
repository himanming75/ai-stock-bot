$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v92_20\output"){Remove-Item "release\v92_20\output" -Recurse -Force}
Write-Host "=== V92.01-V92.20 INSTALL CHECK ==="
python tools/install_check_v92_01_to_v92_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.01-V92.20 TESTS ==="
python -m unittest tools.test_actual_paper_order_submission_dryrun_v92_01_to_v92_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.01-V92.20 PIPELINE ==="
python tools/run_v92_01_to_v92_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.01-V92.20 VERIFY ==="
python tools/verify_v92_01_to_v92_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V92.01-V92.20 PASS - READY TO COMMIT"
