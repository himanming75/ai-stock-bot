$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_v9201_to_v9800_phase1_premarket_completion.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
