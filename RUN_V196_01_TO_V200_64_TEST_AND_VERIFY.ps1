$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v196_01_to_v200_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v196_01_to_v200_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V196_01_TO_V200_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v196_01_to_v200_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V196.01-V200.64 TEST AND VERIFY PASS"
