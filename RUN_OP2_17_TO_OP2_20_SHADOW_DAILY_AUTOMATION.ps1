$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP2.17-OP2.20 SHADOW DAILY AUTOMATION ==="
Write-Host "Local single Shadow runtime tick only. No broker network or orders."

python tools/run_shadow_daily_automation_op2_17_to_op2_20.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP2.17-OP2.20 COMPLETE"
