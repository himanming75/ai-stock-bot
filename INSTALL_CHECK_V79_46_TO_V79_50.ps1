$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_46_to_v79_50.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.46-V79.50 INSTALL CHECK PASS"
