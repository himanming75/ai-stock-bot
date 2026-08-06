[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python .\tools\run_v12001_to_v13000_portfolio_context.py

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
