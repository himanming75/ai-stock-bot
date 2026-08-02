$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op5_13_to_op5_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_promotion_gate_op5_13_to_op5_16 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP5_13_TO_OP5_16_PROMOTION_GATE.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_promotion_gate_op5_13_to_op5_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP5.13-OP5.16 TEST AND VERIFY PASS"
