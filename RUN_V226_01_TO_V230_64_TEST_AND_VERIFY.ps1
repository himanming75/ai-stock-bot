$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v226_01_to_v230_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v226_01_to_v230_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V226_01_TO_V230_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v226_01_to_v230_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V226.01-V230.64 TEST AND VERIFY PASS"
