$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== BUNDLE C R14-R15 UNIT TEST ==="
& $Python -m unittest tools.test_bundle_c_final_operations -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== BUNDLE C R14-R15 FINAL OPERATIONS ==="
& $Python (Join-Path $Root "tools\run_bundle_c_final_operations.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== BUNDLE C R14-R15 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_bundle_c_final_operations.py")
exit $LASTEXITCODE
