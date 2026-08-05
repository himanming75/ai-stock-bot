param(
    [int]$MaxWatchCycles=1
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
    throw "NON-PAPER ENDPOINT BLOCKED"
}

python .\tools\run_automation_watchdog_restart_recovery.py `
    --max-watch-cycles $MaxWatchCycles

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
