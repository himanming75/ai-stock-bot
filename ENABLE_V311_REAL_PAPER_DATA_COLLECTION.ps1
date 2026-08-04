$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$path = ".\release\v311_01_to_v320_64\config\real_paper_data_collection_policy.json"
$typed = Read-Host "Type ENABLE_REAL_PAPER_DATA_COLLECTION"
if($typed -ne "ENABLE_REAL_PAPER_DATA_COLLECTION"){
  throw "Confirmation phrase did not match."
}
$value = Get-Content $path -Raw | ConvertFrom-Json
$value.collector_enabled = $true
$value.paper_read_enabled = $true
$value.paper_submission_enabled = $false
$value.maximum_new_orders_per_day = 0
$value | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8
Write-Host "Real Paper data collection enabled."
Write-Host "This stage is monitor-only and submits zero new orders."
