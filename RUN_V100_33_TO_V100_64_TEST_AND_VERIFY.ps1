$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v100_33_to_v100_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v100_33_to_v100_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V100_33_TO_V100_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v100_33_to_v100_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V100.33-V100.64 TEST AND VERIFY PASS"
