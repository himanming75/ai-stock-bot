param(
    [int]$IntervalSeconds=10,
    [int]$MaxCycles=30
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
    throw "NON-PAPER ENDPOINT BLOCKED"
}

python .\tools\run_p3_partial_fill_handling_validation.py `
    --interval-seconds $IntervalSeconds `
    --max-cycles $MaxCycles

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
