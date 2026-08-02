$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== V140.06-V140.09 ULTRA FAST AUTONOMOUS ENGINE ==="
python tools/run_autonomous_engine_bundle_v140_06_to_v140_09.py --repository-root .
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V140.06-V140.09 COMPLETE"
