$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v95_01_to_v95_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v95_01_to_v95_32 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V95_01_TO_V95_32.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v95_01_to_v95_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V95.01-V95.32 TEST AND VERIFY PASS"
