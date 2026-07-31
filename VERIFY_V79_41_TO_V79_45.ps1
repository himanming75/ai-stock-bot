$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_41_to_v79_45_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.41-V79.45 VERIFY PASS"
