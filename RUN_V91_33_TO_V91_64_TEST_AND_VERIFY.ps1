$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v91_33_to_v91_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v91_33_to_v91_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass -File .\RUN_V91_33_TO_V91_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v91_33_to_v91_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V91.33-V91.64 TEST AND VERIFY PASS"
