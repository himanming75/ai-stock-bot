$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v101_33_to_v101_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v101_33_to_v101_64 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V101_33_TO_V101_64.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools\verify_v101_33_to_v101_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V101.33-V101.64 TEST AND VERIFY PASS"
