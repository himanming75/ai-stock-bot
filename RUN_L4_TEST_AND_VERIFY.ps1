$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== L4 UNIT TEST ==="
& $Python -m unittest tools.test_l4_live_reconciliation_preparation -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L4 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_l4_offline_qualification.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L4 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_l4_live_reconciliation_preparation.py")
exit $LASTEXITCODE
