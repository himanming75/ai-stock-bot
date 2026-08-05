param(
    [Parameter(Mandatory=$true)][string]$Symbol,
    [Parameter(Mandatory=$true)][ValidateSet("buy","sell")][string]$Side,
    [Parameter(Mandatory=$true)][ValidateSet("market","limit")][string]$Type,
    [ValidateSet("day","gtc")][string]$Tif = "day",
    [string]$Qty,
    [string]$Notional,
    [string]$LimitPrice,
    [string]$StrategyId = "manual-p2-validation"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

if ($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets") {
    throw "Only the Alpaca Paper endpoint is permitted."
}
if ($env:ALPACA_PAPER_EXECUTION_NETWORK_ENABLE -ne "true") {
    throw "Set ALPACA_PAPER_EXECUTION_NETWORK_ENABLE=true."
}
if ($env:ALPACA_PAPER_EXECUTION_WRITE_ENABLE -ne "true") {
    throw "Set ALPACA_PAPER_EXECUTION_WRITE_ENABLE=true."
}
if ($env:ALPACA_PAPER_EXECUTION_CONFIRMATION -ne "I_UNDERSTAND_THIS_SUBMITS_A_PAPER_ORDER") {
    throw "Exact Paper order confirmation phrase is required."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Fresh Alpaca Paper credentials are required."
}
if (($Qty -and $Notional) -or (-not $Qty -and -not $Notional)) {
    throw "Provide exactly one of -Qty or -Notional."
}

$KillSwitchPath = Join-Path $Root `
    "release\p1_broker_consolidation\actual\kill_switch.json"
$KillSwitch = Get-Content $KillSwitchPath -Raw | ConvertFrom-Json
if ($KillSwitch.kill_switch_active -ne $false) {
    throw "P1 Kill Switch is active. Do not submit until it is explicitly deactivated."
}

$Arguments = @(
    (Join-Path $Root "tools\run_p2_actual_submit.py"),
    "--symbol", $Symbol,
    "--side", $Side,
    "--type", $Type,
    "--tif", $Tif,
    "--strategy-id", $StrategyId
)
if ($Qty) { $Arguments += @("--qty", $Qty) }
if ($Notional) { $Arguments += @("--notional", $Notional) }
if ($LimitPrice) { $Arguments += @("--limit-price", $LimitPrice) }

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root
    & $Python @Arguments
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
