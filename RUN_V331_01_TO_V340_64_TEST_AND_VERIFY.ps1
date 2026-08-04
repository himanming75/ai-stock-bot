$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "=== V331.01-V340.64 UNIT TEST ==="
& $Python -m unittest tools.test_v331_01_to_v340_64 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V331.01-V340.64 GOVERNANCE RUN ==="
& $Python (Join-Path $Root "tools\run_v331_01_to_v340_64.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== V331.01-V340.64 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_v331_01_to_v340_64.py")
exit $LASTEXITCODE
