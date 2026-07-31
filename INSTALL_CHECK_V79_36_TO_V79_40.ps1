$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_36_to_v79_40.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.36-V79.40 INSTALL CHECK PASS"
