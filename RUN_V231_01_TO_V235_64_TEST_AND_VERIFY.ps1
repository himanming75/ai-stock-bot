$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v231_01_to_v235_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v231_01_to_v235_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V231_01_TO_V235_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v231_01_to_v235_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V231.01-V235.64 TEST AND VERIFY PASS"
