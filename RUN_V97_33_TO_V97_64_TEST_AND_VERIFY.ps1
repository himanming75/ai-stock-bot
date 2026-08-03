$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v97_33_to_v97_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v97_33_to_v97_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V97_33_TO_V97_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v97_33_to_v97_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V97.33-V97.64 TEST AND VERIFY PASS"
