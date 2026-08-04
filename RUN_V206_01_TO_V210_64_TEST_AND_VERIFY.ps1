$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v206_01_to_v210_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v206_01_to_v210_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V206_01_TO_V210_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v206_01_to_v210_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V206.01-V210.64 TEST AND VERIFY PASS"
