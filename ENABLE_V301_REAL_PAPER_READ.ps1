$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$path = ".\release\v301_01_to_v305_64\config\real_paper_validation_policy.json"
$typed = Read-Host "Type ENABLE_REAL_PAPER_READ"
if($typed -ne "ENABLE_REAL_PAPER_READ"){throw "Confirmation phrase did not match."}
$value = Get-Content $path -Raw | ConvertFrom-Json
$value.paper_read_enabled = $true
$value | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8
Write-Host "Real Alpaca Paper read-only validation enabled."
Write-Host "No order submission has been enabled."
