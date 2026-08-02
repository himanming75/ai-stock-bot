$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP5.13-OP5.16 PAPER PILOT PROMOTION GATE ==="
Write-Host "Local eligibility evaluation only. No broker or order operations."

python tools/run_promotion_gate_op5_13_to_op5_16.py `
  --repository-root .

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP5.13-OP5.16 COMPLETE"
