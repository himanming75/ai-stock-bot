$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== V139.06 NEXT ORDER ELIGIBILITY ==="
Write-Host "Local saved-state eligibility only. No credentials, broker network, or order submission."
python tools/run_next_order_eligibility_v139_06.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V139.06 NEXT ORDER ELIGIBILITY COMPLETE"
