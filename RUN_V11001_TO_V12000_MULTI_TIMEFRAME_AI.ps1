[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python .\tools\run_v11001_to_v12000_multi_timeframe_ai.py

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
