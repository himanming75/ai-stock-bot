$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== L5 UNIT TEST ==="
& $Python -m unittest tools.test_l5_live_autonomous_runtime_preparation -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L5 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_l5_offline_qualification.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L5 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_l5_live_autonomous_runtime_preparation.py")
exit $LASTEXITCODE
