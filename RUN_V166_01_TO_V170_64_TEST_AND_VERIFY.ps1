$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v166_01_to_v170_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v166_01_to_v170_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V166_01_TO_V170_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v166_01_to_v170_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V166.01-V170.64 TEST AND VERIFY PASS"
