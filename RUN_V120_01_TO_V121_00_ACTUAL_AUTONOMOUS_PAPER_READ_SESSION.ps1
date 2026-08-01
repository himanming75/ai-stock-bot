$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v121_00\output") {
    Remove-Item "release\v121_00\output" -Recurse -Force
}

Write-Host "=== V120.01-V121.00 INSTALL CHECK ==="
python tools/install_check_v120_01_to_v121_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V120.01-V121.00 REAL UNIT TESTS ==="
python -m unittest tools.test_actual_autonomous_paper_read_session_v120_01_to_v121_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V120.01-V121.00 OFFLINE READ FIXTURE ==="
python tools/run_actual_autonomous_paper_read_fixture_v120_01_to_v121_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V120.01-V121.00 VERIFY ==="
python tools/verify_actual_autonomous_paper_read_session_v120_01_to_v121_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V120.01-V121.00 ACTUAL AUTONOMOUS PAPER READ SESSION PASS - READY TO COMMIT"
