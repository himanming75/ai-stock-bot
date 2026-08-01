$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v90_20\output"){Remove-Item "release\v90_20\output" -Recurse -Force}
Write-Host "=== V90.01-V90.20 INSTALL CHECK ==="
python tools/install_check_v90_01_to_v90_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.01-V90.20 TESTS ==="
python -m unittest tools.test_actual_paper_automation_v90_01_to_v90_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.01-V90.20 PIPELINE (OFFLINE SAFE DEFAULT) ==="
python tools/run_v90_01_to_v90_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.01-V90.20 VERIFY ==="
python tools/verify_v90_01_to_v90_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V90.01-V90.20 PASS - READY TO COMMIT"
