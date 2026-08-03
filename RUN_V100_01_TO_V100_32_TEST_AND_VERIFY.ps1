$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v100_01_to_v100_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v100_01_to_v100_32 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V100_01_TO_V100_32.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v100_01_to_v100_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V100.01-V100.32 TEST AND VERIFY PASS"
