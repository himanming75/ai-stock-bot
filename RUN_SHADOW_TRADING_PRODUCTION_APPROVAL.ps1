$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root
& $Python (
    Join-Path $Root `
    "tools\run_shadow_trading_production_approval.py"
)
exit $LASTEXITCODE
