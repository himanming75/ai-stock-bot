param(
    [string]$Symbols="SPY,QQQ,IWM",
    [int]$IntervalSeconds=60,
    [int]$MaxCycles=10
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

if([string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID)){
    . .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper
}

python .\tools\run_actual_market_coverage_polling_validation.py `
    --symbols $Symbols `
    --interval-seconds $IntervalSeconds `
    --max-cycles $MaxCycles

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
