$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v104_01_to_v104_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v104_01_to_v104_32 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V104_01_TO_V104_32.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v104_01_to_v104_32.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V104.01-V104.32 TEST AND VERIFY PASS"
