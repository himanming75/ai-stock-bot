$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_36_to_v79_40_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.36-V79.40 VERIFY PASS"
