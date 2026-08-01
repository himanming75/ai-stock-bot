$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v82_60\output"){Remove-Item "release\v82_60\output" -Recurse -Force}
Write-Host "=== V82.41-V82.60 INSTALL CHECK ==="
python tools/install_check_v82_41_to_v82_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.41-V82.60 TESTS ==="
python -m unittest tools.test_broker_connection_validation_v82_41_to_v82_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.41-V82.60 PIPELINE ==="
python tools/run_v82_41_to_v82_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.41-V82.60 VERIFY ==="
python tools/verify_v82_41_to_v82_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V82.41-V82.60 PASS - READY TO COMMIT"
