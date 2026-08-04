$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v266_01_to_v270_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v266_01_to_v270_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V266_01_TO_V270_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v266_01_to_v270_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V266.01-V270.64 TEST AND VERIFY PASS"
