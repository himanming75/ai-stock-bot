$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op5_01_to_op5_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_multi_day_paper_validation_op5_01_to_op5_04 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP5_01_TO_OP5_04_VALIDATION.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_multi_day_paper_validation_op5_01_to_op5_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP5.01-OP5.04 TEST AND VERIFY PASS"
