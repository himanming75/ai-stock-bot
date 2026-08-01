$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v88_00\output"){Remove-Item "release\v88_00\output" -Recurse -Force}
Write-Host "=== V87.81-V88.00 INSTALL CHECK ==="
python tools/install_check_v87_81_to_v88_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.81-V88.00 TESTS ==="
python -m unittest tools.test_strategy_operations_rc_v87_81_to_v88_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.81-V88.00 PIPELINE ==="
python tools/run_v87_81_to_v88_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V87.81-V88.00 VERIFY ==="
python tools/verify_v87_81_to_v88_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V87.81-V88.00 PASS - READY TO COMMIT"
