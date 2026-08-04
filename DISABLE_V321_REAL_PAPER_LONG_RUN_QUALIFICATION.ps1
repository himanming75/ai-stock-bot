$PolicyPath = Join-Path $PSScriptRoot "release\v321_01_to_v330_64\config\real_paper_long_run_policy.json"
$Policy = Get-Content $PolicyPath -Raw | ConvertFrom-Json
$Policy.qualification_enabled = $false
$Policy.paper_submission_enabled = $false
$Policy.live_submission_enabled = $false
$Policy.live_network_enabled = $false
$Policy.broker_write_enabled = $false
$Policy.maximum_new_orders_per_day = 0
$Policy | ConvertTo-Json -Depth 20 | Set-Content $PolicyPath -Encoding UTF8
Write-Host "Real Paper long-run qualification disabled."
