$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root

Write-Host "=== OPERATIONAL RESILIENCE UNIT TEST ==="
& $Python -m unittest tools.test_operational_resilience -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== OPERATIONAL RESILIENCE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_operational_resilience.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== OPERATIONAL RESILIENCE VERIFY ==="
& $Python (Join-Path $Root "tools\verify_operational_resilience.py")
exit $LASTEXITCODE
