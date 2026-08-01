$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v88_40\output"){Remove-Item "release\v88_40\output" -Recurse -Force}
Write-Host "=== V88.21-V88.40 INSTALL CHECK ==="
python tools/install_check_v88_21_to_v88_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.21-V88.40 TESTS ==="
python -m unittest tools.test_strategy_runtime_loop_v88_21_to_v88_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.21-V88.40 PIPELINE ==="
python tools/run_v88_21_to_v88_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.21-V88.40 VERIFY ==="
python tools/verify_v88_21_to_v88_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V88.21-V88.40 PASS - READY TO COMMIT"
