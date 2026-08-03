$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v93_33_to_v93_64.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v93_33_to_v93_64 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V93_33_TO_V93_64.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v93_33_to_v93_64.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V93.33-V93.64 TEST AND VERIFY PASS"
