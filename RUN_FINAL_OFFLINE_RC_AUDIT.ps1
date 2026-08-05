$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Project .venv was not found."
}

$env:PYTHONPATH = $Root
& $Python (Join-Path $Root "tools\run_final_offline_rc_audit.py")
exit $LASTEXITCODE
