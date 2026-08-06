$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python .\tools\run_v8401_to_v8600_broker_sync.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
