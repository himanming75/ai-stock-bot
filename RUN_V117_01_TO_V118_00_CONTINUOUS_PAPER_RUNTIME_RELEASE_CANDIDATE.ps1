$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v118_00\output") {
    Remove-Item "release\v118_00\output" -Recurse -Force
}

Write-Host "=== V117.01-V118.00 INSTALL CHECK ==="
python tools/install_check_v117_01_to_v118_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V117.01-V118.00 REAL UNIT TESTS ==="
python -m unittest tools.test_continuous_paper_runtime_v117_01_to_v118_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V117.01-V118.00 CONTINUOUS RUNTIME DEMO ==="
python tools/run_continuous_paper_runtime_v117_01_to_v118_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V117.01-V118.00 VERIFY ==="
python tools/verify_continuous_paper_runtime_v117_01_to_v118_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V117.01-V118.00 CONTINUOUS PAPER RUNTIME RELEASE CANDIDATE PASS - READY TO COMMIT"
