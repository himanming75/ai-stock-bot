$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v98_01_to_v98_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v98_01_to_v98_32 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V98_01_TO_V98_32.ps1 `
    -Force
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v98_01_to_v98_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V98.01-V98.32 TEST AND VERIFY PASS"
