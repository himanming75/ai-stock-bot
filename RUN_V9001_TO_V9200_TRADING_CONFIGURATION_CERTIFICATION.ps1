$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_v9001_to_v9200_trading_configuration_certification.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
