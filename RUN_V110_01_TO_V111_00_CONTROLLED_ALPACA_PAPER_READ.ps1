$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v111_00\output") {
    Remove-Item "release\v111_00\output" -Recurse -Force
}

Write-Host "=== V110.01-V111.00 INSTALL CHECK ==="
python tools/install_check_v110_01_to_v111_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V110.01-V111.00 REAL UNIT TESTS ==="
python -m unittest tools.test_controlled_alpaca_paper_read_v110_01_to_v111_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V110.01-V111.00 OFFLINE READ FIXTURE ==="
python tools/run_controlled_alpaca_paper_read_fixture_v110_01_to_v111_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V110.01-V111.00 VERIFY ==="
python tools/verify_controlled_alpaca_paper_read_v110_01_to_v111_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V110.01-V111.00 CONTROLLED ALPACA PAPER READ VALIDATION PASS - READY TO COMMIT"
