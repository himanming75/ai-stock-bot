$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v146_01_to_v150_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v146_01_to_v150_64 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v146_01_to_v150_64.py
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V146.01-V150.64 TEST AND VERIFY PASS"
