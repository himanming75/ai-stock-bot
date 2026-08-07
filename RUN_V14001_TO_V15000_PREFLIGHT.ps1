[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python .\tools\run_v14001_to_v15000_paper_autonomous_execution.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
