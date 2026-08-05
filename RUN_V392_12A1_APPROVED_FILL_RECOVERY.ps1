$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== V392.12A1 RECOVER APPROVED FILL ==="
    & $Python (Join-Path $Root "tools\recover_v392_11a_approved_fill.py") `
        --project-root $Root
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V392.12A REGRESSION TEST ==="
    & $Python -m unittest tools.test_v392_12a -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V392.12A ACCOUNTING FROM APPROVED SNAPSHOT ==="
    & $Python (Join-Path $Root "tools\run_v392_12a.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V392.12A VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_v392_12a.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
