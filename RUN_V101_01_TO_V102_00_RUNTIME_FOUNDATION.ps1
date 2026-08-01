$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v102_00\output") {
    Remove-Item "release\v102_00\output" -Recurse -Force
}

Write-Host "=== V101.01-V102.00 INSTALL CHECK ==="
python tools/install_check_v101_01_to_v102_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V101.01-V102.00 REAL UNIT TESTS ==="
python -m unittest tools.test_runtime_foundation_v101_01_to_v102_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V101.01-V102.00 RUNTIME DEMO ==="
python tools/run_runtime_foundation_v101_01_to_v102_00.py --repository-root . --ticks 3
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V101.01-V102.00 VERIFY ==="
python tools/verify_runtime_foundation_v101_01_to_v102_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V101.01-V102.00 REAL RUNTIME FOUNDATION PASS - READY TO COMMIT"
