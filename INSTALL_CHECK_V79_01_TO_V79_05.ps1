$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_01_to_v79_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.01-V79.05 INSTALL CHECK PASS"
