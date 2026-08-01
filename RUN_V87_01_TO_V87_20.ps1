$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v87_20\output"){Remove-Item "release\v87_20\output" -Recurse -Force}
Write-Host "=== V87.01-V87.20 INSTALL CHECK ==="
python tools/install_check_v87_01_to_v87_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.01-V87.20 TESTS ==="
python -m unittest tools.test_strategy_execution_operations_v87_01_to_v87_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.01-V87.20 PIPELINE ==="
python tools/run_v87_01_to_v87_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.01-V87.20 VERIFY ==="
python tools/verify_v87_01_to_v87_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V87.01-V87.20 PASS - READY TO COMMIT"
