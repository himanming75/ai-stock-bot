$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_16_to_v79_20.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.16-V79.20 INSTALL CHECK PASS"
