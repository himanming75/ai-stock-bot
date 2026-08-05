$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_dash2_01_to_dash2_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_paper_dashboard_integration_dash2_01_to_dash2_04 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/build_paper_dashboard_snapshot_dash2_01_to_dash2_04.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_paper_dashboard_integration_dash2_01_to_dash2_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "DASH2.01-DASH2.04 TEST AND VERIFY PASS"
