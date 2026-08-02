$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP5.05-OP5.08 MULTI-DAY VALIDATION ANALYTICS ==="
Write-Host "Local validation analytics only. No broker requests or orders."

python tools/run_validation_analytics_op5_05_to_op5_08.py `
  --repository-root .

if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP5.05-OP5.08 COMPLETE"
