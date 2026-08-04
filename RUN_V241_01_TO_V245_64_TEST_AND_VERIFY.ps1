$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v241_01_to_v245_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v241_01_to_v245_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V241_01_TO_V245_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v241_01_to_v245_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V241.01-V245.64 TEST AND VERIFY PASS"
