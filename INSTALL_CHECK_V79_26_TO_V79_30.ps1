$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_26_to_v79_30.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.26-V79.30 INSTALL CHECK PASS"
