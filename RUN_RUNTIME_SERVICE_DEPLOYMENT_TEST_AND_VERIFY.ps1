$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root

Write-Host "=== RUNTIME SERVICE / DEPLOYMENT UNIT TEST ==="
& $Python -m unittest tools.test_runtime_service_deployment -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== RUNTIME SERVICE / DEPLOYMENT QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_runtime_service_deployment.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== RUNTIME SERVICE / DEPLOYMENT VERIFY ==="
& $Python (Join-Path $Root "tools\verify_runtime_service_deployment.py")
exit $LASTEXITCODE
