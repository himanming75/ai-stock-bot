$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path "release\v131_00\output") {
    Remove-Item "release\v131_00\output" -Recurse -Force
}
if (Test-Path "release\v131_00\ledger") {
    Remove-Item "release\v131_00\ledger" -Recurse -Force
}

Write-Host "=== V130.01-V131.00 INSTALL CHECK ==="
python tools/install_check_v130_01_to_v131_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V130.01-V131.00 REAL UNIT TESTS ==="
python -m unittest tools.test_order_completion_next_order_unlock_v130_01_to_v131_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V130.01-V131.00 COMPLETION/UNLOCK GATE ==="
python tools/run_order_completion_next_order_unlock_v130_01_to_v131_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V130.01-V131.00 VERIFY ==="
python tools/verify_order_completion_next_order_unlock_v130_01_to_v131_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V130.01-V131.00 ORDER COMPLETION NEXT ORDER UNLOCK PASS - READY TO COMMIT"
