$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v105_33_to_v105_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v105_33_to_v105_64 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V105_33_TO_V105_64.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools\verify_v105_33_to_v105_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V105.33-V105.64 TEST AND VERIFY PASS"
