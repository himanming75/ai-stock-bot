$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv was not found." }
$env:PYTHONPATH = $Root

Write-Host "=== P2 OFFLINE SAFETY TEST ==="
& $Python -m unittest tools.test_p2_actual_paper_broker_read -v
exit $LASTEXITCODE
