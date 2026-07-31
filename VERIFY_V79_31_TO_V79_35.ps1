$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_31_to_v79_35_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.31-V79.35 VERIFY PASS"
