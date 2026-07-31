$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_11_to_v79_15_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.11-V79.15 VERIFY PASS"
