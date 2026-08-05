$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root
    & $Python (Join-Path $Root "tools\run_p4_actual_runtime_preflight.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
