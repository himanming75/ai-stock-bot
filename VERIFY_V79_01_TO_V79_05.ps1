$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_01_to_v79_05_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.01-V79.05 VERIFY PASS"
