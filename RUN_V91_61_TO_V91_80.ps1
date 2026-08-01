$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v91_80\output"){Remove-Item "release\v91_80\output" -Recurse -Force}
Write-Host "=== V91.61-V91.80 INSTALL CHECK ==="
python tools/install_check_v91_61_to_v91_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.61-V91.80 TESTS ==="
python -m unittest tools.test_actual_paper_automation_rc2_certification_v91_61_to_v91_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.61-V91.80 PIPELINE ==="
python tools/run_v91_61_to_v91_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.61-V91.80 VERIFY ==="
python tools/verify_v91_61_to_v91_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V91.61-V91.80 PASS - READY TO COMMIT"
