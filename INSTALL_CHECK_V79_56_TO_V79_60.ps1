$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_v79_56_to_v79_60.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.56-V79.60 INSTALL CHECK PASS"
