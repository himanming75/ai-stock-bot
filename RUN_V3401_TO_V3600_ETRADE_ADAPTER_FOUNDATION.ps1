$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v3401_to_v3600_etrade_adapter_foundation.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
