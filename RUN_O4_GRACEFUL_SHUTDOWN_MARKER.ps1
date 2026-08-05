param(
    [string]$RuntimeId = "operator-session",
    [string]$Reason = "OPERATOR_STOP",
    [int]$LastCycleNumber = 0
)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root
& $Python `
  (Join-Path $Root "tools\run_o4_graceful_shutdown_marker.py") `
  --runtime-id $RuntimeId `
  --reason $Reason `
  --last-cycle-number $LastCycleNumber
