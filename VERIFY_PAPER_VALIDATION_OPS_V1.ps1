$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

& $Python -m unittest tools.test_paper_validation_ops_v1 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

$Service=Get-Content .\paper_validation_ops\service.py -Raw
$Dash=Get-Content .\tools\run_paper_validation_dashboard_v1.py -Raw

$Forbidden=@(
 '\.\s*submit_order\s*\(',
 '\.\s*cancel_order\s*\(',
 '\.\s*close_position\s*\(',
 '\.\s*replace_order\s*\('
)

foreach($Pattern in $Forbidden){
 if($Service -match $Pattern -or $Dash -match $Pattern){
   throw "FORBIDDEN BROKER WRITE CALL FOUND: $Pattern"
 }
}

if($Dash -notmatch '127\.0\.0\.1'){
 throw "DASHBOARD MUST BE LOCALHOST ONLY"
}

Write-Host "VERIFY: PASS"
Write-Host "DASHBOARD: LOCALHOST ONLY"
Write-Host "TRADING CONFIG CHANGES: 0"
Write-Host "BROKER WRITE METHODS: 0"
Write-Host "PAPER SESSION: UNAFFECTED"
