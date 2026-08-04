$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v106_01_to_v106_32.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v106_01_to_v106_32 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V106_01_TO_V106_32.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools\verify_v106_01_to_v106_32.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V106.01-V106.32 TEST AND VERIFY PASS"
