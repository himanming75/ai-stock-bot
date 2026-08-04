$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V400.01-V410.64 UNIT TEST ==="
& $Python -m unittest tools.test_v400_01_to_v410_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V400.01-V410.64 DRY RUN ==="
& $Python (Join-Path $Root "tools\run_v400_01_to_v410_64.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V400.01-V410.64 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v400_01_to_v410_64.py")
exit $LASTEXITCODE
