$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== V391.04A UNIT TEST ==="
    & $Python -m unittest tools.test_v391_04a -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V391.04A POSITION SIZE GUARD ==="
    & $Python (Join-Path $Root "tools\run_v391_04a.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V391.04A VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_v391_04a.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
