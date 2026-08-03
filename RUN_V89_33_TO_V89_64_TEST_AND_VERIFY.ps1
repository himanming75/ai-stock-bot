$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v89_33_to_v89_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v89_33_to_v89_64 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V89_33_TO_V89_64.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools\verify_v89_33_to_v89_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V89.33-V89.64 TEST AND VERIFY PASS"
