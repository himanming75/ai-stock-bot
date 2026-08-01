$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_51_to_v79_55_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.51-V79.55 VERIFY PASS"
