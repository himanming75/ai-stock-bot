$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools\install_check_v96_01_to_v96_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python -m unittest tools.test_v96_01_to_v96_32 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
    -File .\RUN_V96_01_TO_V96_32.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

python tools\verify_v96_01_to_v96_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

Write-Host "V96.01-V96.32 TEST AND VERIFY PASS"
