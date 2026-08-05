$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

python .\tools\run_daily_session_manager.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
