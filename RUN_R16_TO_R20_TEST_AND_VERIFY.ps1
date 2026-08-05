$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R16-R20 UNIT TEST ==="
& $Python -m unittest tools.test_r16_to_r20 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R16-R20 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_r16_to_r20.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R16-R20 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_r16_to_r20.py")
exit $LASTEXITCODE
