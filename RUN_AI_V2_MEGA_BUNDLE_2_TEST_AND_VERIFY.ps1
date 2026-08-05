$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== AI V2 MEGA BUNDLE 2 UNIT TEST ==="
& $Python -m unittest tools.test_ai_v2_mega_bundle_2 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== AI V2 MEGA BUNDLE 2 OFFLINE QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_ai_v2_mega_bundle_2.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== AI V2 MEGA BUNDLE 2 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_ai_v2_mega_bundle_2.py")
exit $LASTEXITCODE
