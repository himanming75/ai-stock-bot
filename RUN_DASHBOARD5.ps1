param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8780
)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root
Write-Host "Open http://$HostAddress`:$Port"
& $Python (Join-Path $Root "tools\run_dashboard5.py") `
  --host $HostAddress --port $Port
