$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== P4 UNIT TEST ==="
    & $Python -m unittest tools.test_p4_autonomous_paper_runtime -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P4 OFFLINE AUTONOMOUS RUNTIME ==="
    & $Python (Join-Path $Root "tools\run_p4_offline_runtime.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P4 VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_p4_autonomous_paper_runtime.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
