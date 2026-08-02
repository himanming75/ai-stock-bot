$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op4_13_to_op4_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_paper_risk_monitor_op4_13_to_op4_16 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP4_13_TO_OP4_16_RISK_MONITOR.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_paper_risk_monitor_op4_13_to_op4_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.13-OP4.16 TEST AND VERIFY PASS"
