$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v99_33_to_v99_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v99_33_to_v99_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V99_33_TO_V99_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v99_33_to_v99_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V99.33-V99.64 TEST AND VERIFY PASS"
