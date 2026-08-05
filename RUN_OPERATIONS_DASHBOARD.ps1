param(
    [int]$Port = 8765
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root
Write-Host "Open http://127.0.0.1:$Port"
& $Python `
  (Join-Path $Root "tools\run_operations_dashboard.py") `
  --host 127.0.0.1 `
  --port $Port
