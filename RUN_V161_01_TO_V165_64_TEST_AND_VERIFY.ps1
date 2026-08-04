$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v161_01_to_v165_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v161_01_to_v165_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V161_01_TO_V165_64.ps1
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v161_01_to_v165_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V161.01-V165.64 TEST AND VERIFY PASS"
