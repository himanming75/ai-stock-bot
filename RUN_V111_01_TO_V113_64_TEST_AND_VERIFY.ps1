$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v111_01_to_v113_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v111_01_to_v113_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V111_01_TO_V113_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v111_01_to_v113_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V111.01-V113.64 TEST AND VERIFY PASS"
