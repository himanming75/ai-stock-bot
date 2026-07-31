$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_26_to_v79_30_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.26-V79.30 VERIFY PASS"
