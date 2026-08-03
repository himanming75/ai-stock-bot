$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v94_01_to_v94_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v94_01_to_v94_32 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V94_01_TO_V94_32.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v94_01_to_v94_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V94.01-V94.32 TEST AND VERIFY PASS"
