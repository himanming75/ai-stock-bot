$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V341.01-V350.64 UNIT TEST ==="
& $Python -m unittest tools.test_v341_01_to_v350_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V341.01-V350.64 DECISION RUN ==="
& $Python (Join-Path $Root "tools\run_v341_01_to_v350_64.py") --no-ledger
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V341.01-V350.64 REPLAY VERIFY ==="
& $Python (Join-Path $Root "tools\replay_v341_01_to_v350_64.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V341.01-V350.64 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v341_01_to_v350_64.py")
exit $LASTEXITCODE
