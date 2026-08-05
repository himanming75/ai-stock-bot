$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== ACTUAL VALIDATION CONTROL UNIT TEST ==="
& $Python -m unittest tools.test_actual_validation_control_center -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== ACTUAL VALIDATION STATUS ==="
& $Python (Join-Path $Root "tools\run_actual_validation_control_status.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== ACTUAL VALIDATION REPORT ==="
& $Python (Join-Path $Root "tools\run_actual_validation_report.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== ACTUAL VALIDATION CONTROL VERIFY ==="
& $Python (Join-Path $Root "tools\verify_actual_validation_control_center.py")
exit $LASTEXITCODE
