$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V371.01-V380.64 UNIT TEST ==="
& $Python -m unittest tools.test_v371_01_to_v380_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V371.01-V380.64 SAFE DRY RUN ==="
& $Python (Join-Path $Root "tools\run_v371_01_to_v380_64.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V371.01-V380.64 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v371_01_to_v380_64.py")
exit $LASTEXITCODE
