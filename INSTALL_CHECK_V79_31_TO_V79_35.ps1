$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_31_to_v79_35.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.31-V79.35 INSTALL CHECK PASS"
