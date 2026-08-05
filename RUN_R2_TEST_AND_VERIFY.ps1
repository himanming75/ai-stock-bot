$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R2 UNIT TEST ==="
& $Python -m unittest `
  tools.test_r2_windows_scheduler_service_preparation -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R2 WINDOWS READINESS ==="
& $Python (Join-Path $Root "tools\run_r2_windows_readiness.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R2 VERIFY ==="
& $Python `
  (Join-Path $Root "tools\verify_r2_windows_scheduler_service_preparation.py")
exit $LASTEXITCODE
