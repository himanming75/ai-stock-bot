$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root

Write-Host "=== SECURE CONTROL PLANE UNIT TEST ==="
& $Python -m unittest tools.test_secure_control_plane -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== SECURE CONTROL PLANE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_secure_control_plane.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== SECURE CONTROL PLANE VERIFY ==="
& $Python (Join-Path $Root "tools\verify_secure_control_plane.py")
exit $LASTEXITCODE
