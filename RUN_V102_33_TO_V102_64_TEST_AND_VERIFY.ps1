$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools\install_check_v102_33_to_v102_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v102_33_to_v102_64 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V102_33_TO_V102_64.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools\verify_v102_33_to_v102_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V102.33-V102.64 TEST AND VERIFY PASS"
