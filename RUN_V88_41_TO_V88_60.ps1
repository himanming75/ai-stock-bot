$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v88_60\output"){Remove-Item "release\v88_60\output" -Recurse -Force}
Write-Host "=== V88.41-V88.60 INSTALL CHECK ==="
python tools/install_check_v88_41_to_v88_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.41-V88.60 TESTS ==="
python -m unittest tools.test_market_data_operations_v88_41_to_v88_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.41-V88.60 PIPELINE ==="
python tools/run_v88_41_to_v88_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.41-V88.60 VERIFY ==="
python tools/verify_v88_41_to_v88_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V88.41-V88.60 PASS - READY TO COMMIT"
