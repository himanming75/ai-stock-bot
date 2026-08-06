[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python .\tools\run_v13001_to_v14000_portfolio_optimizer.py

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
