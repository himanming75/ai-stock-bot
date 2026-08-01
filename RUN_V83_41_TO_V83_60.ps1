$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v83_60\output"){Remove-Item "release\v83_60\output" -Recurse -Force}
Write-Host "=== V83.41-V83.60 INSTALL CHECK ==="
python tools/install_check_v83_41_to_v83_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.41-V83.60 TESTS ==="
python -m unittest tools.test_paper_order_submission_sim_v83_41_to_v83_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.41-V83.60 PIPELINE ==="
python tools/run_v83_41_to_v83_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.41-V83.60 VERIFY ==="
python tools/verify_v83_41_to_v83_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V83.41-V83.60 PASS - READY TO COMMIT"
