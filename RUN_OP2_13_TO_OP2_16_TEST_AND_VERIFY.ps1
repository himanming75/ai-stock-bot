$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_op2_13_to_op2_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_automatic_shadow_signal_pipeline_op2_13_to_op2_16 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_OP2_13_TO_OP2_16_SHADOW_PIPELINE.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_automatic_shadow_signal_pipeline_op2_13_to_op2_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP2.13-OP2.16 TEST AND VERIFY PASS"
