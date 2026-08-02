$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V139.03 NEXT CYCLE UNLOCK ==="
Write-Host "Local saved-state unlock only. No credentials, broker network, or order submission."

python tools/run_next_cycle_unlock_v139_03.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.03 NEXT CYCLE UNLOCK COMPLETE"
