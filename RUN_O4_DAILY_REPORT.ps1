param(
    [string]$TradingDay = ""
)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }
$env:PYTHONPATH = $Root
$argsList = @((Join-Path $Root "tools\run_o4_daily_report.py"))
if ($TradingDay) { $argsList += @("--trading-day", $TradingDay) }
& $Python @argsList
