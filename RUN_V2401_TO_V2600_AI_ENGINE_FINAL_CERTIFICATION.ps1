$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_v2401_to_v2600_ai_engine_final_certification.py --repository-root "."
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
