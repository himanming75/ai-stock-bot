$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v121_01_to_v123_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v121_01_to_v123_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V121_01_TO_V123_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v121_01_to_v123_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V121.01-V123.64 TEST AND VERIFY PASS"
