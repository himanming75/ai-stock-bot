$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v171_01_to_v175_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v171_01_to_v175_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V171_01_TO_V175_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v171_01_to_v175_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V171.01-V175.64 TEST AND VERIFY PASS"
