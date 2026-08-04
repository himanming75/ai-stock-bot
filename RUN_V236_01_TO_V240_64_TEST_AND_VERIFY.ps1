$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v236_01_to_v240_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v236_01_to_v240_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V236_01_TO_V240_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v236_01_to_v240_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V236.01-V240.64 TEST AND VERIFY PASS"
