$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v361_to_v370_notification_alert_routing.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
