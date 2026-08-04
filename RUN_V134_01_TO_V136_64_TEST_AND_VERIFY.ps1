$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v134_01_to_v136_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v134_01_to_v136_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V134_01_TO_V136_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v134_01_to_v136_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V134.01-V136.64 TEST AND VERIFY PASS"
