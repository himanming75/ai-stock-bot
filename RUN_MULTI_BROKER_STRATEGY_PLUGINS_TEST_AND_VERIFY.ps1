$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root

Write-Host "=== MULTI-BROKER / STRATEGY PLUGIN UNIT TEST ==="
& $Python -m unittest tools.test_multi_broker_strategy_plugins -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== MULTI-BROKER / STRATEGY PLUGIN QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_multi_broker_strategy_plugins.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== MULTI-BROKER / STRATEGY PLUGIN VERIFY ==="
& $Python (Join-Path $Root "tools\verify_multi_broker_strategy_plugins.py")
exit $LASTEXITCODE
