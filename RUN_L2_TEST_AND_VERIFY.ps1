$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== L2 UNIT TEST ==="
& $Python -m unittest tools.test_l2_live_read_only_preparation -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L2 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_l2_offline_qualification.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L2 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_l2_live_read_only_preparation.py")
exit $LASTEXITCODE
