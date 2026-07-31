$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_06_to_v79_10.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.06-V79.10 INSTALL CHECK PASS"
