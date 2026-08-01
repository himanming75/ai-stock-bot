$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v92_40\output"){Remove-Item "release\v92_40\output" -Recurse -Force}
Write-Host "=== V92.21-V92.40 INSTALL CHECK ==="
python tools/install_check_v92_21_to_v92_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.21-V92.40 TESTS ==="
python -m unittest tools.test_actual_paper_order_submission_gate_v92_21_to_v92_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.21-V92.40 PIPELINE ==="
python tools/run_v92_21_to_v92_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V92.21-V92.40 VERIFY ==="
python tools/verify_v92_21_to_v92_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V92.21-V92.40 PASS - READY TO COMMIT"
