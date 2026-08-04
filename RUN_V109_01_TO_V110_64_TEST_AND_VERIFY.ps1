$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v109_01_to_v110_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v109_01_to_v110_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V109_01_TO_V110_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v109_01_to_v110_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V109.01-V110.64 TEST AND VERIFY PASS"
