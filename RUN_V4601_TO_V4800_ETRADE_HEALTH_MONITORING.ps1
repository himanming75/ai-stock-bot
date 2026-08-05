$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v4601_to_v4800_etrade_health_monitoring.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
