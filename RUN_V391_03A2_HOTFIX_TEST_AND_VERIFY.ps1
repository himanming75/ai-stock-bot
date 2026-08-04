$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$PreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== V391.03A2 VERIFY IMPORT PATH ==="
    & $Python (Join-Path $Root "tools\verify_v391_03a2_hotfix.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V391.01A REGRESSION TEST ==="
    & $Python -m unittest tools.test_v391_01a -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V391.02A REGRESSION TEST ==="
    & $Python -m unittest tools.test_v391_02a -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V391.03A UNIT TEST ==="
    & $Python -m unittest tools.test_v391_03a -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V391.03A RUN ==="
    & $Python (Join-Path $Root "tools\run_v391_03a.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V391.03A VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_v391_03a.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
}
