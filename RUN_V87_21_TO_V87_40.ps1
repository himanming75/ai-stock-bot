$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v87_40\output"){Remove-Item "release\v87_40\output" -Recurse -Force}
Write-Host "=== V87.21-V87.40 INSTALL CHECK ==="
python tools/install_check_v87_21_to_v87_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.21-V87.40 TESTS ==="
python -m unittest tools.test_strategy_execution_simulation_v87_21_to_v87_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.21-V87.40 PIPELINE ==="
python tools/run_v87_21_to_v87_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.21-V87.40 VERIFY ==="
python tools/verify_v87_21_to_v87_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V87.21-V87.40 PASS - READY TO COMMIT"
