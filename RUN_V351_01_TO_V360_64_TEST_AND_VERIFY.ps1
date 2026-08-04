$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V351.01-V360.64 UNIT TEST ==="
& $Python -m unittest tools.test_v351_01_to_v360_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V351.01-V360.64 PROPOSAL RUN ==="
& $Python (Join-Path $Root "tools\run_v351_01_to_v360_64.py") --no-ledger
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V351.01-V360.64 REPLAY VERIFY ==="
& $Python (Join-Path $Root "tools\replay_v351_01_to_v360_64.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V351.01-V360.64 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v351_01_to_v360_64.py")
exit $LASTEXITCODE
