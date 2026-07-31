$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_21_to_v79_25_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.21-V79.25 VERIFY PASS"
