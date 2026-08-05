$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== V461-V470 UNIT TEST ==="
    & $Python -m unittest tools.test_v461_to_v470 -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V470.64 OFFLINE READ-SAFETY RUN ==="
    & $Python (Join-Path $Root "tools\run_v461_to_v470.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== V470.64 VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_v461_to_v470.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
