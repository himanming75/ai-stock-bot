param(
    [Parameter(Mandatory=$true)][string]$ClientOrderId,
    [Parameter(Mandatory=$true)][ValidateSet("AAPL","SPY","QQQ")][string]$Symbol,
    [Parameter(Mandatory=$true)][ValidateSet("buy","sell")][string]$Side,
    [Parameter(Mandatory=$true)][decimal]$Quantity,
    [Parameter(Mandatory=$true)][decimal]$LastFilledQuantity,
    [Parameter(Mandatory=$true)][string]$LastStatus,
    [string]$BrokerOrderId = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL ALPACA PAPER ORDER READ-ONLY RECOVERY ==="
Write-Host "This script sends GET requests only and cannot submit or cancel an order."

if ($env:AI_STOCK_BOT_ENABLE_ALPACA_PAPER_ORDER_RECOVERY -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_ALPACA_PAPER_ORDER_RECOVERY=YES"
}
if ($env:AI_STOCK_BOT_ALPACA_PAPER_ORDER_RECOVERY_CONFIRMATION -ne "RECOVER ONE EXISTING ALPACA PAPER ORDER READ ONLY") {
    throw "Set the exact recovery confirmation text."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY to PAPER credentials."
}
if (-not $ClientOrderId.StartsWith("BOT-PAPER-ONE-")) {
    throw "ClientOrderId must begin with BOT-PAPER-ONE-"
}

$argsList = @(
    "tools/run_actual_alpaca_paper_order_recovery_v113_01_to_v114_00.py",
    "--repository-root", ".",
    "--client-order-id", $ClientOrderId,
    "--symbol", $Symbol,
    "--side", $Side,
    "--quantity", $Quantity,
    "--last-filled-quantity", $LastFilledQuantity,
    "--last-status", $LastStatus
)
if ($BrokerOrderId) {
    $argsList += @("--broker-order-id", $BrokerOrderId)
}
python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "ACTUAL ALPACA PAPER ORDER RECOVERY COMPLETE"
