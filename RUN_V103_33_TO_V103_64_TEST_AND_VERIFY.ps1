$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v103_33_to_v103_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v103_33_to_v103_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V103_33_TO_V103_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v103_33_to_v103_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V103.33-V103.64 TEST AND VERIFY PASS"
