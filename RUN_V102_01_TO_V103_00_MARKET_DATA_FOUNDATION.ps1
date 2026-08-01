$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v103_00\output") {
    Remove-Item "release\v103_00\output" -Recurse -Force
}

Write-Host "=== V102.01-V103.00 INSTALL CHECK ==="
python tools/install_check_v102_01_to_v103_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V102.01-V103.00 REAL UNIT TESTS ==="
python -m unittest tools.test_market_data_foundation_v102_01_to_v103_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V102.01-V103.00 OFFLINE FIXTURE STREAM ==="
python tools/run_market_data_foundation_v102_01_to_v103_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V102.01-V103.00 VERIFY ==="
python tools/verify_market_data_foundation_v102_01_to_v103_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V102.01-V103.00 REAL MARKET DATA FOUNDATION PASS - READY TO COMMIT"
