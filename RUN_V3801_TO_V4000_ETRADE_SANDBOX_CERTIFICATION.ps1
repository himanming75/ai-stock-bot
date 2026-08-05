$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_v3801_to_v4000_etrade_sandbox_certification.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
