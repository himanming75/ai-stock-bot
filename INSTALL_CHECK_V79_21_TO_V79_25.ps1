$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_21_to_v79_25.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.21-V79.25 INSTALL CHECK PASS"
