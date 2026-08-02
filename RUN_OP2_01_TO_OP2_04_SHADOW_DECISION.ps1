$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP2.01-OP2.04 SHADOW DECISION BOOTSTRAP ==="
Write-Host "Generates BUY/SELL/HOLD shadow decisions only. No broker network or orders."

python tools/run_shadow_decision_bootstrap_op2_01_to_op2_04.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP2.01-OP2.04 COMPLETE"
