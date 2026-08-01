$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v84_60\output"){Remove-Item "release\v84_60\output" -Recurse -Force}
Write-Host "=== V84.41-V84.60 INSTALL CHECK ==="
python tools/install_check_v84_41_to_v84_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.41-V84.60 TESTS ==="
python -m unittest tools.test_live_order_authorization_v84_41_to_v84_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.41-V84.60 PIPELINE ==="
python tools/run_v84_41_to_v84_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.41-V84.60 VERIFY ==="
python tools/verify_v84_41_to_v84_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V84.41-V84.60 PASS - READY TO COMMIT"
