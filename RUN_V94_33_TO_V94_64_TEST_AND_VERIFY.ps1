$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v94_33_to_v94_64.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v94_33_to_v94_64 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V94_33_TO_V94_64.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v94_33_to_v94_64.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V94.33-V94.64 TEST AND VERIFY PASS"
