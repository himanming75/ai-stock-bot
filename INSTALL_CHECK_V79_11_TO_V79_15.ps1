$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_11_to_v79_15.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.11-V79.15 INSTALL CHECK PASS"
