$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V141.01-V141.05 OPERATIONAL STABILITY ==="
Write-Host "Local audit, process lock, retry policy, ledger integrity, and health checks only."

python tools/run_operational_stability_bundle_v141_01_to_v141_05.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V141.01-V141.05 COMPLETE"
