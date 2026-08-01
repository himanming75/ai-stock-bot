$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v91_00\output"){Remove-Item "release\v91_00\output" -Recurse -Force}
Write-Host "=== V90.81-V91.00 INSTALL CHECK ==="
python tools/install_check_v90_81_to_v91_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.81-V91.00 TESTS ==="
python -m unittest tools.test_final_paper_automation_certification_v90_81_to_v91_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.81-V91.00 PIPELINE ==="
python tools/run_v90_81_to_v91_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.81-V91.00 VERIFY ==="
python tools/verify_v90_81_to_v91_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V90.81-V91.00 PASS - READY TO COMMIT"
