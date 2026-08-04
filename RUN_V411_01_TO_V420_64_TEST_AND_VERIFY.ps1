$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V411.01-V420.64 UNIT TEST ==="
& $Python -m unittest tools.test_v411_01_to_v420_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V411.01-V420.64 DRY RUN ==="
& $Python (Join-Path $Root "tools\run_v411_01_to_v420_64.py") --no-memory
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V411.01-V420.64 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v411_01_to_v420_64.py")
exit $LASTEXITCODE
