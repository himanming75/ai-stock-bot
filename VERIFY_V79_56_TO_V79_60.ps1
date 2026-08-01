$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/verify_v79_56_to_v79_60_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.56-V79.60 VERIFY PASS"
