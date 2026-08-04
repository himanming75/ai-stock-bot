$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v251_01_to_v255_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v251_01_to_v255_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V251_01_TO_V255_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v251_01_to_v255_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V251.01-V255.64 TEST AND VERIFY PASS"
