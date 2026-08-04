$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v137_01_to_v139_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v137_01_to_v139_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V137_01_TO_V139_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v137_01_to_v139_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V137.01-V139.64 TEST AND VERIFY PASS"
