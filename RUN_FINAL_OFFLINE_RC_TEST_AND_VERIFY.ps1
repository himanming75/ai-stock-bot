$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Project .venv was not found."
}

$env:PYTHONPATH = $Root

Write-Host "=== FINAL OFFLINE RC UNIT TEST ==="
& $Python -m unittest tools.test_final_offline_rc_audit -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== FINAL OFFLINE RC AUDIT ==="
& $Python (Join-Path $Root "tools\run_final_offline_rc_audit.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== FINAL OFFLINE RC VERIFY ==="
& $Python (Join-Path $Root "tools\verify_final_offline_rc_audit.py")
exit $LASTEXITCODE
