$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (Test-Path "release\v124_00\output") { Remove-Item "release\v124_00\output" -Recurse -Force }
Write-Host "=== V123.01-V124.00 INSTALL CHECK ==="
python tools/install_check_v123_01_to_v124_00.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V123.01-V124.00 REAL UNIT TESTS ==="
python -m unittest tools.test_autonomous_order_ledger_recovery_v123_01_to_v124_00 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V123.01-V124.00 LEDGER RECOVERY DEMO ==="
python tools/run_autonomous_order_ledger_recovery_v123_01_to_v124_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "=== V123.01-V124.00 VERIFY ==="
python tools/verify_autonomous_order_ledger_recovery_v123_01_to_v124_00.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V123.01-V124.00 AUTONOMOUS ORDER LEDGER RECOVERY PASS - READY TO COMMIT"
