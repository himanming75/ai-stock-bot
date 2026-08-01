$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v82_20\output"){Remove-Item "release\v82_20\output" -Recurse -Force}
Write-Host "=== V82.01-V82.20 INSTALL CHECK ==="
python tools/install_check_v82_01_to_v82_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.01-V82.20 TESTS ==="
python -m unittest tools.test_live_safety_foundation_v82_01_to_v82_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.01-V82.20 PIPELINE ==="
python tools/run_v82_01_to_v82_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V82.01-V82.20 VERIFY ==="
python tools/verify_v82_01_to_v82_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V82.01-V82.20 PASS - READY TO COMMIT"
