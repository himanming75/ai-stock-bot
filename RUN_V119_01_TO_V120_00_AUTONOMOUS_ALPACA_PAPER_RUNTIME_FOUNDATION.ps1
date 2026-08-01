$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v120_00\output") {
    Remove-Item "release\v120_00\output" -Recurse -Force
}

Write-Host "=== V119.01-V120.00 INSTALL CHECK ==="
python tools/install_check_v119_01_to_v120_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V119.01-V120.00 REAL UNIT TESTS ==="
python -m unittest tools.test_autonomous_alpaca_paper_runtime_v119_01_to_v120_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V119.01-V120.00 AUTONOMOUS PAPER FOUNDATION DEMO ==="
python tools/run_autonomous_alpaca_paper_runtime_v119_01_to_v120_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V119.01-V120.00 VERIFY ==="
python tools/verify_autonomous_alpaca_paper_runtime_v119_01_to_v120_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V119.01-V120.00 AUTONOMOUS ALPACA PAPER RUNTIME FOUNDATION PASS - READY TO COMMIT"
