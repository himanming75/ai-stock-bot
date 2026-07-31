$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_16_to_v79_20_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.16-V79.20 VERIFY PASS"
