$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V442.01 UNIT TEST ==="
& $Python -m unittest tools.test_v442_01 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V442.01 DRY RUN ==="
& $Python (Join-Path $Root "tools\run_v442_01.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V442.01 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v442_01.py")
exit $LASTEXITCODE
