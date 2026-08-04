$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v221_01_to_v225_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v221_01_to_v225_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V221_01_TO_V225_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v221_01_to_v225_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V221.01-V225.64 TEST AND VERIFY PASS"
