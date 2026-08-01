$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v116_00\output") {
    Remove-Item "release\v116_00\output" -Recurse -Force
}

Write-Host "=== V115.01-V116.00 INSTALL CHECK ==="
python tools/install_check_v115_01_to_v116_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V115.01-V116.00 REAL UNIT TESTS ==="
python -m unittest tools.test_paper_runtime_scheduler_integration_v115_01_to_v116_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V115.01-V116.00 RUNTIME SCHEDULER INTEGRATION DEMO ==="
python tools/run_paper_runtime_scheduler_integration_v115_01_to_v116_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V115.01-V116.00 VERIFY ==="
python tools/verify_paper_runtime_scheduler_integration_v115_01_to_v116_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V115.01-V116.00 PAPER RUNTIME SCHEDULER INTEGRATION PASS - READY TO COMMIT"
