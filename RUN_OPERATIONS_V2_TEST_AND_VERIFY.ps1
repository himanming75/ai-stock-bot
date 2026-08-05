$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== OPERATIONS V2 UNIT TEST ==="
& $Python -m unittest tools.test_operations_v2 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== OPERATIONS V2 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_operations_v2.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== OPERATIONS V2 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_operations_v2.py")
exit $LASTEXITCODE
