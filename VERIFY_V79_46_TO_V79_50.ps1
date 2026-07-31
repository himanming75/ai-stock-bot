$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_46_to_v79_50_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.46-V79.50 VERIFY PASS"
