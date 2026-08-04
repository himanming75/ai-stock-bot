$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v281_01_to_v290_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v281_01_to_v290_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V281_01_TO_V290_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v281_01_to_v290_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V281.01-V290.64 TEST AND VERIFY PASS"
