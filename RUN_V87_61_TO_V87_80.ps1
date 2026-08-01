$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v87_80\output"){Remove-Item "release\v87_80\output" -Recurse -Force}
Write-Host "=== V87.61-V87.80 INSTALL CHECK ==="
python tools/install_check_v87_61_to_v87_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.61-V87.80 TESTS ==="
python -m unittest tools.test_strategy_execution_final_certification_v87_61_to_v87_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.61-V87.80 PIPELINE ==="
python tools/run_v87_61_to_v87_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.61-V87.80 VERIFY ==="
python tools/verify_v87_61_to_v87_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V87.61-V87.80 PASS - READY TO COMMIT"
