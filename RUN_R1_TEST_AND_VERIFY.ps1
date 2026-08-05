$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R1 UNIT TEST ==="
& $Python -m unittest tools.test_r1_production_deployment_preparation -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R1 DEPLOYMENT READINESS ==="
& $Python (Join-Path $Root "tools\run_r1_deployment_readiness.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R1 RELEASE CERTIFICATE GATE ==="
& $Python (Join-Path $Root "tools\run_r1_release_certificate.py")
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 2) {
    exit $LASTEXITCODE
}

Write-Host "=== R1 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_r1_production_deployment_preparation.py")
exit $LASTEXITCODE
