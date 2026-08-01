$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v85_00\output"){Remove-Item "release\v85_00\output" -Recurse -Force}
Write-Host "=== V84.81-V85.00 INSTALL CHECK ==="
python tools/install_check_v84_81_to_v85_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.81-V85.00 TESTS ==="
python -m unittest tools.test_live_broker_final_cert_v84_81_to_v85_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.81-V85.00 PIPELINE ==="
python tools/run_v84_81_to_v85_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.81-V85.00 VERIFY ==="
python tools/verify_v84_81_to_v85_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V84.81-V85.00 PASS - READY TO COMMIT"
