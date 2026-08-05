$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root

Write-Host "=== FEATURE ENGINE / AUTO OPTIMIZATION UNIT TEST ==="
& $Python -m unittest tools.test_feature_engine_auto_optimization -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== FEATURE ENGINE / AUTO OPTIMIZATION QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_feature_engine_auto_optimization.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== FEATURE ENGINE / AUTO OPTIMIZATION VERIFY ==="
& $Python (Join-Path $Root "tools\verify_feature_engine_auto_optimization.py")
exit $LASTEXITCODE
