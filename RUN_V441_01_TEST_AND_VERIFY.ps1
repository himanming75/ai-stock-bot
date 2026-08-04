$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V441.01 UNIT TEST ==="
& $Python -m unittest tools.test_v441_01 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V441.01 DRY RUN ==="
& $Python (Join-Path $Root "tools\run_v441_01.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V441.01 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v441_01.py")
exit $LASTEXITCODE
