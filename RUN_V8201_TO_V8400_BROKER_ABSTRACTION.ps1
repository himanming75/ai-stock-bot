$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_v8201_to_v8400_broker_abstraction.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
