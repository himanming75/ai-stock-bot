$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v91_60\output"){Remove-Item "release\v91_60\output" -Recurse -Force}
Write-Host "=== V91.41-V91.60 INSTALL CHECK ==="
python tools/install_check_v91_41_to_v91_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.41-V91.60 TESTS ==="
python -m unittest tools.test_actual_paper_automation_rc2_v91_41_to_v91_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.41-V91.60 PIPELINE ==="
python tools/run_v91_41_to_v91_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V91.41-V91.60 VERIFY ==="
python tools/verify_v91_41_to_v91_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V91.41-V91.60 PASS - READY TO COMMIT"
