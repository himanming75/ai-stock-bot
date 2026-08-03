$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v92_33_to_v92_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v92_33_to_v92_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass -File .\RUN_V92_33_TO_V92_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v92_33_to_v92_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V92.33-V92.64 TEST AND VERIFY PASS"
