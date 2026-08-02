$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V139.08 SUBMITTED ORDER ACCEPTANCE VERIFICATION ==="
Write-Host "Local submission-result verification only. No credentials, broker network, or order submission."

python tools/run_submitted_order_acceptance_verification_v139_08.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.08 SUBMITTED ORDER ACCEPTANCE VERIFICATION COMPLETE"
