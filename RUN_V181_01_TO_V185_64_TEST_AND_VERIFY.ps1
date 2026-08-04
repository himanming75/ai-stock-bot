$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v181_01_to_v185_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v181_01_to_v185_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V181_01_TO_V185_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v181_01_to_v185_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V181.01-V185.64 TEST AND VERIFY PASS"
