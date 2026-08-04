$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v129_01_to_v130_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v129_01_to_v130_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V129_01_TO_V130_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v129_01_to_v130_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V129.01-V130.64 TEST AND VERIFY PASS"
