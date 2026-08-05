$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_v3201_to_v3400_alpaca_adapter_extraction.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
