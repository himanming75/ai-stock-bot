$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_41_to_v79_45.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.41-V79.45 INSTALL CHECK PASS"
