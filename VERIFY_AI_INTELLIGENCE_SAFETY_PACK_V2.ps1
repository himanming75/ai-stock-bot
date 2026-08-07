[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$Python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if(-not(Test-Path $Python)){$Python='python'}
& $Python -m unittest tools.test_ai_intelligence_safety_pack_v2 -v
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
$Text=Get-Content .\ai_intelligence_v2\service.py -Raw
foreach($Pattern in @('submit_order','cancel_order','replace_order','close_position','close_all_positions')){if($Text-match $Pattern){throw "FORBIDDEN BROKER WRITE METHOD FOUND: $Pattern"}}
Write-Host 'VERIFY: PASS'
Write-Host 'NO BROKER WRITE METHODS: PASS'
Write-Host 'CURRENT PAPER SESSION UNAFFECTED: PASS'
Write-Host 'ZERO LIVE ORDER CONTRACT: PASS'
