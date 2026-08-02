$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_dash1_05_to_dash1_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_dashboard_advanced_dash1_05_to_dash1_08 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/build_dashboard_advanced_snapshot_dash1_05_to_dash1_08.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_dashboard_advanced_dash1_05_to_dash1_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "DASH1.05-DASH1.08 TEST AND VERIFY PASS"
