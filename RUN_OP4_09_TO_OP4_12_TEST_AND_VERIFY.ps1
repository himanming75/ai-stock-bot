$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op4_09_to_op4_12.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_paper_performance_collector_op4_09_to_op4_12 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP4_09_TO_OP4_12_PERFORMANCE.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_paper_performance_collector_op4_09_to_op4_12.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.09-OP4.12 TEST AND VERIFY PASS"
