$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Project .venv was not found."
}

$env:PYTHONPATH = $Root

Write-Host "=== FINAL OFFLINE RC CREDENTIAL SCAN HOTFIX V2 TEST ==="
& $Python -m unittest `
  tools.test_final_offline_rc_credential_scan_hotfix_v2 -v
exit $LASTEXITCODE
