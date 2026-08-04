$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v114_01_to_v116_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v114_01_to_v116_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V114_01_TO_V116_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v114_01_to_v116_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V114.01-V116.64 TEST AND VERIFY PASS"
