$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root
    & $Python (Join-Path $Root "tools\run_v391_07a.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
