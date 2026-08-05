$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv was not found." }
$env:PYTHONPATH = $Root
& $Python (
    Join-Path $Root `
    "tools\verify_p2_actual_paper_broker_read.py"
)
exit $LASTEXITCODE
