$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root
    Write-Host "=== P2A SAFETY HOTFIX UNIT TEST ==="
    & $Python -m unittest tools.test_p2a_notional_safety -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P2 REGRESSION UNIT TEST ==="
    & $Python -m unittest tools.test_p2_actual_paper_execution -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P2A VERIFY ==="
    & $Python (Join-Path $Root "tools\run_p2a_hotfix_verify.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
