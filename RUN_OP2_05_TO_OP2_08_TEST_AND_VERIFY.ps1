$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_op2_05_to_op2_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_shadow_performance_evaluation_op2_05_to_op2_08 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_OP2_05_TO_OP2_08_SHADOW_PERFORMANCE.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_shadow_performance_evaluation_op2_05_to_op2_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP2.05-OP2.08 TEST AND VERIFY PASS"
