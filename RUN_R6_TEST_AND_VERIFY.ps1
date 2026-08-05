$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R6 UNIT TEST ==="
& $Python -m unittest tools.test_r6_runtime_session_manager -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R6 SESSION PREVIEW ==="
& $Python (Join-Path $Root "tools\run_r6_session_preview.py") `
  --profile "paper_ultra_short.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R6 VERIFY ==="
& $Python (Join-Path $Root "tools\verify_r6_runtime_session_manager.py")
exit $LASTEXITCODE
