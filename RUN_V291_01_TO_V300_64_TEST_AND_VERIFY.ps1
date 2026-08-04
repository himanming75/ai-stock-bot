$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v291_01_to_v300_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v291_01_to_v300_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V291_01_TO_V300_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v291_01_to_v300_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V291.01-V300.64 TEST AND VERIFY PASS"
