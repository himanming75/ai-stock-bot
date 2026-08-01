$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v91_20\output"){Remove-Item "release\v91_20\output" -Recurse -Force}
Write-Host "=== V91.01-V91.20 INSTALL CHECK ==="
python tools/install_check_v91_01_to_v91_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.01-V91.20 TESTS ==="
python -m unittest tools.test_actual_paper_automation_optin_v91_01_to_v91_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.01-V91.20 PIPELINE ==="
python tools/run_v91_01_to_v91_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.01-V91.20 VERIFY ==="
python tools/verify_v91_01_to_v91_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V91.01-V91.20 PASS - READY TO COMMIT"
