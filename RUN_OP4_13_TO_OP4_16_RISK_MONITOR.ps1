$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP4.13-OP4.16 PAPER RISK MONITOR ==="
Write-Host "Local risk evaluation only. No broker cancellation or position close."

python tools/run_paper_risk_monitor_op4_13_to_op4_16.py `
  --repository-root .

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.13-OP4.16 COMPLETE"
