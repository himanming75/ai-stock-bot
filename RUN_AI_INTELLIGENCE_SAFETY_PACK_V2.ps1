[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$Python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if(-not(Test-Path $Python)){$Python='python'}
& $Python .\tools\run_ai_intelligence_safety_pack_v2.py --repository-root $PSScriptRoot
exit $LASTEXITCODE
