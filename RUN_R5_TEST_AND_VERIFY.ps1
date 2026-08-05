$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root

Write-Host "=== R5 UNIT TEST ==="
& $Python -m unittest `
  tools.test_r5_runtime_configuration_bridge -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R5 RUNTIME BRIDGE PREVIEW ==="
& $Python `
  (Join-Path $Root "tools\run_r5_runtime_bridge_preview.py") `
  --profile "paper_ultra_short.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== R5 VERIFY ==="
& $Python `
  (Join-Path $Root "tools\verify_r5_runtime_configuration_bridge.py")
exit $LASTEXITCODE
