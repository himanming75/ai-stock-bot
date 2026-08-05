$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v3601_to_v3800_etrade_oauth_session.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
