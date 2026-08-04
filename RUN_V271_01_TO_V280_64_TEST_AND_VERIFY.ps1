$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v271_01_to_v280_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v271_01_to_v280_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V271_01_TO_V280_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v271_01_to_v280_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V271.01-V280.64 TEST AND VERIFY PASS"
