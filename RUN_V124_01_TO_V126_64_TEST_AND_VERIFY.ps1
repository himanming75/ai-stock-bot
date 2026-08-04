$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v124_01_to_v126_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v124_01_to_v126_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V124_01_TO_V126_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v124_01_to_v126_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V124.01-V126.64 TEST AND VERIFY PASS"
