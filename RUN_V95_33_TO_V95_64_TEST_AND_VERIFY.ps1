$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v95_33_to_v95_64.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v95_33_to_v95_64 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V95_33_TO_V95_64.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v95_33_to_v95_64.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V95.33-V95.64 TEST AND VERIFY PASS"
