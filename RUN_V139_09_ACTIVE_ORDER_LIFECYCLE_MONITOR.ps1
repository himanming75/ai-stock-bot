$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V139.09 ACTIVE ORDER LIFECYCLE MONITOR ==="
Write-Host "Local lifecycle snapshot monitoring only. No credentials, broker network, or order submission."

python tools/run_active_order_lifecycle_monitor_v139_09.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.09 ACTIVE ORDER LIFECYCLE MONITOR COMPLETE"
