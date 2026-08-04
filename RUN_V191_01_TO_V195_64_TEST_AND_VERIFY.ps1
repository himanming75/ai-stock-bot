$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v191_01_to_v195_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v191_01_to_v195_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V191_01_TO_V195_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v191_01_to_v195_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V191.01-V195.64 TEST AND VERIFY PASS"
