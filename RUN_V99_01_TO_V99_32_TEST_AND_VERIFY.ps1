$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v99_01_to_v99_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v99_01_to_v99_32 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_V99_01_TO_V99_32.ps1;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v99_01_to_v99_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V99.01-V99.32 TEST AND VERIFY PASS"
