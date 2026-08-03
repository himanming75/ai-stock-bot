$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op5_17_to_op5_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_promotion_approval_op5_17_to_op5_20 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP5_17_TO_OP5_20_APPROVAL.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_promotion_approval_op5_17_to_op5_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP5.17-OP5.20 TEST AND VERIFY PASS"
