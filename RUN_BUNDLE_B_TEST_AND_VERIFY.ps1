$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== BUNDLE B R11-R13 UNIT TEST ==="
& $Python -m unittest tools.test_bundle_b_broker_multi_account -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== BUNDLE B R11-R13 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_bundle_b_broker_multi_account.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== BUNDLE B R11-R13 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_bundle_b_broker_multi_account.py")
exit $LASTEXITCODE
