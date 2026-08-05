$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== O4 UNIT TEST ==="
& $Python -m unittest tools.test_o4_runtime_resume_session_reporting -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O4 RESUME PLAN ==="
& $Python (Join-Path $Root "tools\run_o4_resume_plan.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O4 OPERATOR CHECKLIST ==="
& $Python (Join-Path $Root "tools\run_o4_operator_checklist.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O4 SESSION ROTATION ==="
& $Python (Join-Path $Root "tools\run_o4_session_rotation.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O4 DAILY REPORT ==="
& $Python (Join-Path $Root "tools\run_o4_daily_report.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O4 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_o4_runtime_resume_session_reporting.py")
exit $LASTEXITCODE
