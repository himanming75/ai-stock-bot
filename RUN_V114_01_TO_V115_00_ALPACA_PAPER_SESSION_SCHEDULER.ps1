$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v115_00\output") {
    Remove-Item "release\v115_00\output" -Recurse -Force
}

Write-Host "=== V114.01-V115.00 INSTALL CHECK ==="
python tools/install_check_v114_01_to_v115_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V114.01-V115.00 REAL UNIT TESTS ==="
python -m unittest tools.test_alpaca_paper_session_scheduler_v114_01_to_v115_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V114.01-V115.00 SESSION SCHEDULER DEMO ==="
python tools/run_alpaca_paper_session_scheduler_v114_01_to_v115_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V114.01-V115.00 VERIFY ==="
python tools/verify_alpaca_paper_session_scheduler_v114_01_to_v115_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V114.01-V115.00 ALPACA PAPER SESSION SCHEDULER PASS - READY TO COMMIT"
