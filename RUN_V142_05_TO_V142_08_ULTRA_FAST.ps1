$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== V142.05-V142.08 SCHEDULED RUNTIME AND RECOVERY ==="
Write-Host "Local schedule validation and one controlled resume point only. No broker network or orders."
python tools/run_scheduled_runtime_bundle_v142_05_to_v142_08.py --repository-root .
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V142.05-V142.08 COMPLETE"
