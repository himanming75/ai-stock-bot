$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_dash1_01_to_dash1_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_dashboard_foundation_dash1_01_to_dash1_04 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/build_dashboard_snapshot_dash1_01_to_dash1_04.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_dashboard_foundation_dash1_01_to_dash1_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DASH1.01-DASH1.04 TEST AND VERIFY PASS"
