$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v83_80\output"){Remove-Item "release\v83_80\output" -Recurse -Force}
Write-Host "=== V83.61-V83.80 INSTALL CHECK ==="
python tools/install_check_v83_61_to_v83_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.61-V83.80 TESTS ==="
python -m unittest tools.test_paper_broker_execution_sim_v83_61_to_v83_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.61-V83.80 PIPELINE ==="
python tools/run_v83_61_to_v83_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.61-V83.80 VERIFY ==="
python tools/verify_v83_61_to_v83_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V83.61-V83.80 PASS - READY TO COMMIT"
