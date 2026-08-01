$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Test-Path "release\v80_05\output") {
    Remove-Item "release\v80_05\output" -Recurse -Force
}
Write-Host "=== V80.01-V80.05 INSTALL CHECK ==="
python tools/install_check_v80_01_to_v80_05.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V80.01-V80.05 TESTS ==="
python -m unittest tools.test_paper_trading_readiness_v80_01_to_v80_05 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V80.01-V80.05 PIPELINE ==="
python tools/run_v80_01_to_v80_05_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V80.01-V80.05 VERIFY ==="
python tools/verify_v80_01_to_v80_05_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V80.01-V80.05 PASS - READY TO COMMIT"
