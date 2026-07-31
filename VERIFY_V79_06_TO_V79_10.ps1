$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_06_to_v79_10_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.06-V79.10 VERIFY PASS"
