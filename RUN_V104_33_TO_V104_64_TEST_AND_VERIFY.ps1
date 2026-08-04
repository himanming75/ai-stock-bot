$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v104_33_to_v104_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v104_33_to_v104_64 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V104_33_TO_V104_64.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools\verify_v104_33_to_v104_64.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V104.33-V104.64 TEST AND VERIFY PASS"
