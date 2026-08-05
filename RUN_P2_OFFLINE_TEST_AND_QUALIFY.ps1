$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== P2 UNIT TEST ==="
    & $Python -m unittest tools.test_p2_actual_paper_execution -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P2 OFFLINE QUALIFICATION ==="
    & $Python (Join-Path $Root "tools\run_p2_offline_qualification.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P2 OFFLINE VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_p2_offline_qualification.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
