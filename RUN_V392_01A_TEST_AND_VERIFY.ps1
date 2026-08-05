$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== V392.01A UNIT TEST ==="
    & $Python -m unittest tools.test_v392_01a -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V392.01A EXECUTION AUTHORIZATION ==="
    & $Python (Join-Path $Root "tools\run_v392_01a.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V392.01A VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_v392_01a.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
