$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_51_to_v79_55.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.51-V79.55 INSTALL CHECK PASS"
