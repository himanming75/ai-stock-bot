$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v91_01_to_v91_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v91_01_to_v91_32 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V91_01_TO_V91_32.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v91_01_to_v91_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V91.01-V91.32 TEST AND VERIFY PASS"
