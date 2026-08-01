$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v80_80\output"){Remove-Item "release\v80_80\output" -Recurse -Force}
Write-Host "=== V80.61-V80.80 INSTALL CHECK ==="
python tools/install_check_v80_61_to_v80_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.61-V80.80 TESTS ==="
python -m unittest tools.test_strategy_engine_foundation_v80_61_to_v80_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.61-V80.80 PIPELINE ==="
python tools/run_v80_61_to_v80_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.61-V80.80 VERIFY ==="
python tools/verify_v80_61_to_v80_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V80.61-V80.80 PASS - READY TO COMMIT"
