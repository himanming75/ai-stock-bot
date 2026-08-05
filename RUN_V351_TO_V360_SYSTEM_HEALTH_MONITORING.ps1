$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v351_to_v360_system_health_monitoring.py `
    --repository-root "C:\stock-bot"

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
