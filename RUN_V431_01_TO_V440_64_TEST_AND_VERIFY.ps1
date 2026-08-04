$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V431.01-V440.64 UNIT TEST ==="
& $Python -m unittest tools.test_v431_01_to_v440_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V431.01-V440.64 DRY RUN ==="
& $Python (Join-Path $Root "tools\run_v431_01_to_v440_64.py") --no-memory
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V431.01-V440.64 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v431_01_to_v440_64.py")
exit $LASTEXITCODE
