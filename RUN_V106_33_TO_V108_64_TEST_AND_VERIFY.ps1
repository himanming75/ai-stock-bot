$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v106_33_to_v108_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v106_33_to_v108_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V106_33_TO_V108_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v106_33_to_v108_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V106.33-V108.64 TEST AND VERIFY PASS"
