$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v90_40\output"){Remove-Item "release\v90_40\output" -Recurse -Force}
Write-Host "=== V90.21-V90.40 INSTALL CHECK ==="
python tools/install_check_v90_21_to_v90_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.21-V90.40 TESTS ==="
python -m unittest tools.test_actual_paper_read_runtime_v90_21_to_v90_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.21-V90.40 PIPELINE ==="
python tools/run_v90_21_to_v90_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.21-V90.40 VERIFY ==="
python tools/verify_v90_21_to_v90_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V90.21-V90.40 PASS - READY TO COMMIT"
