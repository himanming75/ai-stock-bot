$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v83_00\output"){Remove-Item "release\v83_00\output" -Recurse -Force}
Write-Host "=== V82.81-V83.00 INSTALL CHECK ==="
python tools/install_check_v82_81_to_v83_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.81-V83.00 TESTS ==="
python -m unittest tools.test_paper_broker_enablement_v82_81_to_v83_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.81-V83.00 PIPELINE ==="
python tools/run_v82_81_to_v83_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.81-V83.00 VERIFY ==="
python tools/verify_v82_81_to_v83_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V82.81-V83.00 PASS - READY TO COMMIT"
