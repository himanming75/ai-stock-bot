param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8770
)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root
Write-Host "Open http://$HostAddress`:$Port"
& $Python (Join-Path $Root "tools\run_operations_v2_dashboard.py") `
  --host $HostAddress --port $Port
