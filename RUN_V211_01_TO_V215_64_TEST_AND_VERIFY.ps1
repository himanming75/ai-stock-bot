$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v211_01_to_v215_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v211_01_to_v215_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V211_01_TO_V215_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v211_01_to_v215_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V211.01-V215.64 TEST AND VERIFY PASS"
