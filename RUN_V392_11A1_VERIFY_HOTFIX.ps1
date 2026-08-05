$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== V392.11A1 HOTFIX UNIT TEST ==="
    & $Python -m unittest tools.test_v392_11a1 -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V392.11A ORIGINAL REGRESSION TEST ==="
    & $Python -m unittest tools.test_v392_11a -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V392.11A1 RE-RUN SIMULATOR ==="
    & $Python (Join-Path $Root "tools\run_v392_11a.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V392.11A1 REPLAY-AWARE VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_v392_11a.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
