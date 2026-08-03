$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
python tools\install_check_v90_01_to_v90_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_v90_01_to_v90_32 -v;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\export_dashboard_analytics_v3.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
python tools\verify_v90_01_to_v90_32.py;if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
Write-Host "V90.01-V90.32 TEST AND VERIFY PASS"
