$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools\install_check_v101_01_to_v101_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v101_01_to_v101_32 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V101_01_TO_V101_32.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v101_01_to_v101_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V101.01-V101.32 TEST AND VERIFY PASS"
