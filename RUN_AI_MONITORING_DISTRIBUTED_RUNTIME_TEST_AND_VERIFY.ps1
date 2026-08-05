$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root

Write-Host "=== AI MONITORING / DISTRIBUTED RUNTIME UNIT TEST ==="
& $Python -m unittest tools.test_ai_monitoring_distributed_runtime -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== AI MONITORING / DISTRIBUTED RUNTIME QUALIFICATION ==="
& $Python (Join-Path $Root "tools\run_ai_monitoring_distributed_runtime.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== AI MONITORING / DISTRIBUTED RUNTIME VERIFY ==="
& $Python (Join-Path $Root "tools\verify_ai_monitoring_distributed_runtime.py")
exit $LASTEXITCODE
