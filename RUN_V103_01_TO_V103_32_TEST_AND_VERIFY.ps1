$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools\install_check_v103_01_to_v103_32.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v103_01_to_v103_32 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V103_01_TO_V103_32.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools\verify_v103_01_to_v103_32.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V103.01-V103.32 TEST AND VERIFY PASS"
