$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v176_01_to_v180_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v176_01_to_v180_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V176_01_TO_V180_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v176_01_to_v180_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V176.01-V180.64 TEST AND VERIFY PASS"
