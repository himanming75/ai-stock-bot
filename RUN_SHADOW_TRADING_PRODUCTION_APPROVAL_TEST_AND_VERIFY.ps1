$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root

Write-Host "=== SHADOW TRADING / PRODUCTION APPROVAL UNIT TEST ==="
& $Python -m unittest `
  tools.test_shadow_trading_production_approval -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== SHADOW TRADING / PRODUCTION APPROVAL QUALIFICATION ==="
& $Python (
    Join-Path $Root `
    "tools\run_shadow_trading_production_approval.py"
)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== SHADOW TRADING / PRODUCTION APPROVAL VERIFY ==="
& $Python (
    Join-Path $Root `
    "tools\verify_shadow_trading_production_approval.py"
)
exit $LASTEXITCODE
