$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v82_40\output"){Remove-Item "release\v82_40\output" -Recurse -Force}
Write-Host "=== V82.21-V82.40 INSTALL CHECK ==="
python tools/install_check_v82_21_to_v82_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.21-V82.40 TESTS ==="
python -m unittest tools.test_broker_read_only_v82_21_to_v82_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.21-V82.40 PIPELINE ==="
python tools/run_v82_21_to_v82_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.21-V82.40 VERIFY ==="
python tools/verify_v82_21_to_v82_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V82.21-V82.40 PASS - READY TO COMMIT"
