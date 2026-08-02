$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools/install_check_v140_10_to_v140_12.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m unittest tools.test_alpaca_paper_integration_bundle_v140_10_to_v140_12 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
powershell -ExecutionPolicy Bypass -File .\RUN_V140_10_TO_V140_12_ULTRA_FAST.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_alpaca_paper_integration_bundle_v140_10_to_v140_12.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V140.10-V140.12 TEST AND VERIFY PASS"
