param(
    [string]$Symbol="SPY",
    [string]$Notional="5",
    [string]$PriceMultiplier="0.50"
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python .\tools\create_p3_cancel_validation_plan.py `
    --symbol $Symbol `
    --notional $Notional `
    --price-multiplier $PriceMultiplier

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
