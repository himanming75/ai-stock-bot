$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== P3 UNIT TEST ==="
    & $Python -m unittest tools.test_p3_order_fill_portfolio_sync -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P3 OFFLINE SYNC ==="
    & $Python (Join-Path $Root "tools\run_p3_offline_sync.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P3 VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_p3_order_fill_portfolio_sync.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
