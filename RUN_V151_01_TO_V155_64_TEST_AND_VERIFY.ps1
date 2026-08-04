$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v151_01_to_v155_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v151_01_to_v155_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v151_01_to_v155_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V151.01-V155.64 TEST AND VERIFY PASS"
