param(
    [string]$TradingDay = "",
    [string]$Reason = "OPERATOR_PREPARED_SESSION"
)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root
$argsList = @((Join-Path $Root "tools\run_o4_session_rotation.py"))
if ($TradingDay) { $argsList += @("--trading-day", $TradingDay) }
$argsList += @("--reason", $Reason)
& $Python @argsList
