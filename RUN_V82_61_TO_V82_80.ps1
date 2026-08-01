$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v82_80\output"){Remove-Item "release\v82_80\output" -Recurse -Force}
Write-Host "=== V82.61-V82.80 INSTALL CHECK ==="
python tools/install_check_v82_61_to_v82_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.61-V82.80 TESTS ==="
python -m unittest tools.test_dry_run_broker_validation_v82_61_to_v82_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.61-V82.80 PIPELINE ==="
python tools/run_v82_61_to_v82_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.61-V82.80 VERIFY ==="
python tools/verify_v82_61_to_v82_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V82.61-V82.80 PASS - READY TO COMMIT"
