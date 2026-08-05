param(
    [string]$Symbol="SPY",
    [string]$Notional="5"
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python .\tools\create_p3_micro_paper_ticket.py `
    --symbol $Symbol `
    --notional $Notional

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
