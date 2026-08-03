$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v93_01_to_v93_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v93_01_to_v93_32 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V93_01_TO_V93_32.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v93_01_to_v93_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V93.01-V93.32 TEST AND VERIFY PASS"
