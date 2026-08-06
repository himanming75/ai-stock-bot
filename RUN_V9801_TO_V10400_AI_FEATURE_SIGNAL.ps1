[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python .\tools\run_v9801_to_v10400_ai_feature_signal.py

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
