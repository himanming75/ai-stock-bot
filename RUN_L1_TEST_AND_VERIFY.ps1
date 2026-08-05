$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== L1 UNIT TEST ==="
& $Python -m unittest tools.test_l1_live_safety_boundary -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L1 LIVE SAFETY BOUNDARY ==="
& $Python (Join-Path $Root "tools\run_l1_live_safety_boundary.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L1 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_l1_live_safety_boundary.py")
exit $LASTEXITCODE
