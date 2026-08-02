$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== V140.02-V140.05 ULTRA FAST RUNTIME CONTROL ==="
Write-Host "Local market, risk, cycle, and health gates only."
python tools/run_runtime_control_bundle_v140_02_to_v140_05.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V140.02-V140.05 ULTRA FAST RUNTIME CONTROL COMPLETE"
