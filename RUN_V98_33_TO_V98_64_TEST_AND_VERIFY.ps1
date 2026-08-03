$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v98_33_to_v98_64.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v98_33_to_v98_64 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V98_33_TO_V98_64.ps1 -NoResume;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v98_33_to_v98_64.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V98.33-V98.64 TEST AND VERIFY PASS"
