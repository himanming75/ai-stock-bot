$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v88_80\output"){Remove-Item "release\v88_80\output" -Recurse -Force}
Write-Host "=== V88.61-V88.80 INSTALL CHECK ==="
python tools/install_check_v88_61_to_v88_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.61-V88.80 TESTS ==="
python -m unittest tools.test_scheduler_runtime_simulation_v88_61_to_v88_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.61-V88.80 PIPELINE ==="
python tools/run_v88_61_to_v88_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.61-V88.80 VERIFY ==="
python tools/verify_v88_61_to_v88_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V88.61-V88.80 PASS - READY TO COMMIT"
