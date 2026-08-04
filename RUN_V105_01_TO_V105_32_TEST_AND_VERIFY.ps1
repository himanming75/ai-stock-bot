$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v105_01_to_v105_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v105_01_to_v105_32 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V105_01_TO_V105_32.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v105_01_to_v105_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V105.01-V105.32 TEST AND VERIFY PASS"
