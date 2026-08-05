$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== L6 UNIT TEST ==="
& $Python -m unittest tools.test_l6_live_long_run_qualification_preparation -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L6 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_l6_offline_qualification.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L6 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_l6_live_long_run_qualification_preparation.py")
exit $LASTEXITCODE
