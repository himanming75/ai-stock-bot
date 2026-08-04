$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v117_01_to_v119_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v117_01_to_v119_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V117_01_TO_V119_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v117_01_to_v119_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V117.01-V119.64 TEST AND VERIFY PASS"
