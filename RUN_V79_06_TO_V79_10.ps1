$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$OutputDir = Join-Path $PSScriptRoot "release\v79_10\output"
if (Test-Path $OutputDir) {
    Write-Host "=== CLEARING STALE V79.10 OUTPUT ==="
    Remove-Item $OutputDir -Recurse -Force
}

Write-Host "=== V79.06-V79.10 INSTALL CHECK ==="
python tools/install_check_v79_06_to_v79_10.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V79.06-V79.10 TESTS ==="
python -m unittest tools.test_alpaca_historical_data_v79_06_to_v79_10 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V79.06-V79.10 PIPELINE ==="
python tools/run_v79_06_to_v79_10_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V79.06-V79.10 VERIFY ==="
python tools/verify_v79_06_to_v79_10_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V79.06-V79.10 PASS - READY TO COMMIT"
