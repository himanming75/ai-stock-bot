$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== L3 UNIT TEST ==="
& $Python -m unittest tools.test_l3_live_micro_execution_preparation -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L3 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_l3_offline_qualification.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== L3 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_l3_live_micro_execution_preparation.py")
exit $LASTEXITCODE
