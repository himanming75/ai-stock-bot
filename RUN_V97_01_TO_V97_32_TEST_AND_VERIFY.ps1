$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v97_01_to_v97_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v97_01_to_v97_32 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V97_01_TO_V97_32.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v97_01_to_v97_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V97.01-V97.32 TEST AND VERIFY PASS"
