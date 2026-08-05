$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== OPERATIONS BUNDLE UNIT TEST ==="
& $Python -m unittest tools.test_operations_bundle -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== OPERATIONS MONITOR VALIDATION ==="
& $Python (Join-Path $Root "tools\run_operations_install_validation.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L1 SAFETY PREPARATION ==="
& $Python (Join-Path $Root "tools\run_l1_safety_preparation.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== OPERATIONS BUNDLE VERIFY ==="
& $Python (Join-Path $Root "tools\verify_operations_bundle.py")
exit $LASTEXITCODE
