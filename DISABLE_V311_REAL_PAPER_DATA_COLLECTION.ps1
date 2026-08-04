$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$path = ".\release\v311_01_to_v320_64\config\real_paper_data_collection_policy.json"
$value = Get-Content $path -Raw | ConvertFrom-Json
$value.collector_enabled = $false
$value.paper_read_enabled = $false
$value | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8
Write-Host "Real Paper data collection disabled."
