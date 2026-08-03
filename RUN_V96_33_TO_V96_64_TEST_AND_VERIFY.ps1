$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v96_33_to_v96_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v96_33_to_v96_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V96_33_TO_V96_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v96_33_to_v96_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V96.33-V96.64 TEST AND VERIFY PASS"
