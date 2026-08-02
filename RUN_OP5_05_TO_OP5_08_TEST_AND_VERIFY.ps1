$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op5_05_to_op5_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_validation_analytics_op5_05_to_op5_08 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP5_05_TO_OP5_08_ANALYTICS.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_validation_analytics_op5_05_to_op5_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP5.05-OP5.08 TEST AND VERIFY PASS"
