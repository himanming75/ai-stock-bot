$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v127_01_to_v128_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v127_01_to_v128_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V127_01_TO_V128_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v127_01_to_v128_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V127.01-V128.64 TEST AND VERIFY PASS"
