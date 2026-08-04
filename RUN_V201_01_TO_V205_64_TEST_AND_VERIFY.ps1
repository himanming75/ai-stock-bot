$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v201_01_to_v205_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v201_01_to_v205_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V201_01_TO_V205_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v201_01_to_v205_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V201.01-V205.64 TEST AND VERIFY PASS"
