$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V139.04 RECOVERY VALIDATION ==="
Write-Host "Local saved-state recovery audit only. No credentials, broker network, or order submission."

python tools/run_recovery_validation_v139_04.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.04 RECOVERY VALIDATION COMPLETE"
