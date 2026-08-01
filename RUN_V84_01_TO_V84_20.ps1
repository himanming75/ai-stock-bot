$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v84_20\output"){Remove-Item "release\v84_20\output" -Recurse -Force}
Write-Host "=== V84.01-V84.20 INSTALL CHECK ==="
python tools/install_check_v84_01_to_v84_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.01-V84.20 TESTS ==="
python -m unittest tools.test_live_broker_enablement_v84_01_to_v84_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.01-V84.20 PIPELINE ==="
python tools/run_v84_01_to_v84_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.01-V84.20 VERIFY ==="
python tools/verify_v84_01_to_v84_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V84.01-V84.20 PASS - READY TO COMMIT"
