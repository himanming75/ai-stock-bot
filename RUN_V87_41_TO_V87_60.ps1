$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v87_60\output"){Remove-Item "release\v87_60\output" -Recurse -Force}
Write-Host "=== V87.41-V87.60 INSTALL CHECK ==="
python tools/install_check_v87_41_to_v87_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.41-V87.60 TESTS ==="
python -m unittest tools.test_strategy_execution_reconciliation_v87_41_to_v87_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.41-V87.60 PIPELINE ==="
python tools/run_v87_41_to_v87_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.41-V87.60 VERIFY ==="
python tools/verify_v87_41_to_v87_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V87.41-V87.60 PASS - READY TO COMMIT"
