[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python .\tools\run_v10401_to_v11000_ai_signal_scoring.py

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
