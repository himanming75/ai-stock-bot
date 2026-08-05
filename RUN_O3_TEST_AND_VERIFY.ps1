$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== O3 UNIT TEST ==="
& $Python -m unittest tools.test_o3_autonomous_operations -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O3 HEALTH SCORE ==="
& $Python (Join-Path $Root "tools\run_o3_health_score.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O3 RESOURCE SAMPLE ==="
& $Python (Join-Path $Root "tools\run_o3_resource_sample.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O3 DIAGNOSTICS ==="
& $Python (Join-Path $Root "tools\run_o3_diagnostics.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O3 AUDIT EXPORT ==="
& $Python (Join-Path $Root "tools\run_o3_audit_export.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== O3 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_o3_autonomous_operations.py")
exit $LASTEXITCODE
