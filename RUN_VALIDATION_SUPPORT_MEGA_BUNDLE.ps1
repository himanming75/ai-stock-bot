$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Project virtual environment was not found."
}
$env:PYTHONPATH = $Root
& $Python (
    Join-Path $Root `
    "tools\run_validation_support_mega_bundle.py"
)
exit $LASTEXITCODE
