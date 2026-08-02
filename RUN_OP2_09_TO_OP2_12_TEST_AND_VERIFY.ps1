$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_op2_09_to_op2_12.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_multi_day_shadow_validation_op2_09_to_op2_12 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_OP2_09_TO_OP2_12_MULTI_DAY_SHADOW.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_multi_day_shadow_validation_op2_09_to_op2_12.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP2.09-OP2.12 TEST AND VERIFY PASS"
