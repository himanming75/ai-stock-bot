$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v90_80\output"){Remove-Item "release\v90_80\output" -Recurse -Force}
Write-Host "=== V90.61-V90.80 INSTALL CHECK ==="
python tools/install_check_v90_61_to_v90_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.61-V90.80 TESTS ==="
python -m unittest tools.test_actual_paper_release_candidate_v90_61_to_v90_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.61-V90.80 PIPELINE ==="
python tools/run_v90_61_to_v90_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V90.61-V90.80 VERIFY ==="
python tools/verify_v90_61_to_v90_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V90.61-V90.80 PASS - READY TO COMMIT"
