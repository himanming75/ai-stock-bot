param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8791
)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Project .venv not found." }
$env:PYTHONPATH = $Root
Write-Host "Open http://$HostAddress`:$Port"
& $Python (Join-Path $Root "tools\run_secure_operator_console.py") `
  --host $HostAddress --port $Port
