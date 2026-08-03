$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v92_01_to_v92_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v92_01_to_v92_32 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass -File .\RUN_V92_01_TO_V92_32.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v92_01_to_v92_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V92.01-V92.32 TEST AND VERIFY PASS"
