$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== BUNDLE A R7-R10 UNIT TEST ==="
& $Python -m unittest tools.test_bundle_a_runtime_core -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== BUNDLE A R7-R10 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_bundle_a_runtime_core.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== BUNDLE A R7-R10 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_bundle_a_runtime_core.py")
exit $LASTEXITCODE
