$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== O2 UNIT TEST ==="
& $Python -m unittest tools.test_o2_operations_enhancement -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O2 WATCHDOG ==="
& $Python (Join-Path $Root "tools\run_o2_watchdog.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O2 SCHEDULER MONITOR ==="
& $Python (Join-Path $Root "tools\run_o2_scheduler_monitor.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O2 RECOVERY SNAPSHOT ==="
& $Python (Join-Path $Root "tools\run_o2_recovery_snapshot.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O2 NOTIFICATION DEFAULT-OFF TEST ==="
& $Python (Join-Path $Root "tools\run_o2_notification_test.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O2 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_o2_operations_enhancement.py")
exit $LASTEXITCODE
