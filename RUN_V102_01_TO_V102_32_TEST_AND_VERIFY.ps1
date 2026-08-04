$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools\install_check_v102_01_to_v102_32.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v102_01_to_v102_32 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V102_01_TO_V102_32.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools\verify_v102_01_to_v102_32.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V102.01-V102.32 TEST AND VERIFY PASS"
