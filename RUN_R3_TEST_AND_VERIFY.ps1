$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R3 UNIT TEST ==="
& $Python -m unittest tools.test_r3_secure_credential_storage -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R3 VAULT STATUS ==="
& $Python (Join-Path $Root "tools\run_r3_vault_status.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R3 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_r3_secure_credential_storage.py")
exit $LASTEXITCODE
