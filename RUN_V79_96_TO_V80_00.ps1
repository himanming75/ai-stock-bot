$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Test-Path "release\v80_00\output") {
    Remove-Item "release\v80_00\output" -Recurse -Force
}
Write-Host "=== V79.96-V80.00 INSTALL CHECK ==="
python tools/install_check_v79_96_to_v80_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.96-V80.00 TESTS ==="
python -m unittest tools.test_historical_backtest_completion_v79_96_to_v80_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.96-V80.00 PIPELINE ==="
python tools/run_v79_96_to_v80_00_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V79.96-V80.00 VERIFY ==="
python tools/verify_v79_96_to_v80_00_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V79.96-V80.00 PASS - READY TO COMMIT"
