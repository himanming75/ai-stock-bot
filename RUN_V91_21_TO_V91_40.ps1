$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v91_40\output"){Remove-Item "release\v91_40\output" -Recurse -Force}
Write-Host "=== V91.21-V91.40 INSTALL CHECK ==="
python tools/install_check_v91_21_to_v91_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.21-V91.40 TESTS ==="
python -m unittest tools.test_actual_paper_automation_session_v91_21_to_v91_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.21-V91.40 PIPELINE ==="
python tools/run_v91_21_to_v91_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.21-V91.40 VERIFY ==="
python tools/verify_v91_21_to_v91_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V91.21-V91.40 PASS - READY TO COMMIT"
