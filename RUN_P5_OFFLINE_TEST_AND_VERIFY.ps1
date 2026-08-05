$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root

    Write-Host "=== P5 UNIT TEST ==="
    & $Python -m unittest tools.test_p5_paper_long_run_qualification -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P5 OFFLINE 1000-CYCLE QUALIFICATION ==="
    & $Python (Join-Path $Root "tools\run_p5_offline_qualification.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== P5 VERIFY ==="
    & $Python (Join-Path $Root "tools\verify_p5_paper_long_run_qualification.py")
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
