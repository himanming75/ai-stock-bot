$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== V143 FINAL PRODUCTION RELEASE ==="
Write-Host "Builds final Paper-only package. Automatic start, broker network, and orders remain disabled."
python tools/run_final_production_release_v143.py --repository-root .
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V143 FINAL PRODUCTION RELEASE COMPLETE"
