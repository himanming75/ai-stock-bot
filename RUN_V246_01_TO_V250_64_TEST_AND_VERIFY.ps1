$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v246_01_to_v250_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v246_01_to_v250_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V246_01_TO_V250_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v246_01_to_v250_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V246.01-V250.64 TEST AND VERIFY PASS"
