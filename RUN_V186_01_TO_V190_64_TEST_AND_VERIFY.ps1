$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v186_01_to_v190_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v186_01_to_v190_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V186_01_TO_V190_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v186_01_to_v190_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V186.01-V190.64 TEST AND VERIFY PASS"
