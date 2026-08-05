$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R1A AUDIT SCAN PERFORMANCE TEST ==="
& $Python -m unittest tools.test_r1a_deployment_audit_scan_performance -v
exit $LASTEXITCODE
