$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v84_00\output"){Remove-Item "release\v84_00\output" -Recurse -Force}
Write-Host "=== V83.81-V84.00 INSTALL CHECK ==="
python tools/install_check_v83_81_to_v84_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.81-V84.00 TESTS ==="
python -m unittest tools.test_paper_broker_final_cert_v83_81_to_v84_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.81-V84.00 PIPELINE ==="
python tools/run_v83_81_to_v84_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.81-V84.00 VERIFY ==="
python tools/verify_v83_81_to_v84_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V83.81-V84.00 PASS - READY TO COMMIT"
