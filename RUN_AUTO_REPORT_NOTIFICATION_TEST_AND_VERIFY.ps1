$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root

Write-Host "=== AUTO REPORT / NOTIFICATION UNIT TEST ==="
& $Python -m unittest tools.test_auto_report_notification -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== AUTO REPORT / NOTIFICATION QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_auto_report_notification.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== AUTO REPORT / NOTIFICATION VERIFY ==="
& $Python (Join-Path $Root "tools\verify_auto_report_notification.py")
exit $LASTEXITCODE
