$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v216_01_to_v220_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v216_01_to_v220_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V216_01_TO_V220_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v216_01_to_v220_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V216.01-V220.64 TEST AND VERIFY PASS"
