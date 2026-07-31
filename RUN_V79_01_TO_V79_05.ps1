$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V79.01-V79.05 INSTALL CHECK ==="
python tools/install_check_v79_01_to_v79_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V79.01-V79.05 TESTS ==="
python -m unittest tools.test_alpaca_market_data_foundation_v79_01_to_v79_05 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V79.01-V79.05 PIPELINE ==="
python tools/run_v79_01_to_v79_05_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V79.01-V79.05 VERIFY ==="
python tools/verify_v79_01_to_v79_05_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V79.01-V79.05 PASS - READY TO COMMIT"
