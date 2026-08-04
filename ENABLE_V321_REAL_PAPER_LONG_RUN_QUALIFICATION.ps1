$Expected = "ENABLE_REAL_PAPER_LONG_RUN_QUALIFICATION"
$Typed = Read-Host "Type $Expected"
if ($Typed -ne $Expected) { Write-Error "Confirmation text did not match."; exit 1 }
$PolicyPath = Join-Path $PSScriptRoot "release\v321_01_to_v330_64\config\real_paper_long_run_policy.json"
$Policy = Get-Content $PolicyPath -Raw | ConvertFrom-Json
$Policy.qualification_enabled = $true
$Policy.paper_submission_enabled = $false
$Policy.live_submission_enabled = $false
$Policy.live_network_enabled = $false
$Policy.broker_write_enabled = $false
$Policy.maximum_new_orders_per_day = 0
$Policy | ConvertTo-Json -Depth 20 | Set-Content $PolicyPath -Encoding UTF8
Write-Host "Real Paper long-run qualification enabled."
Write-Host "Monitor-only. New Paper and Live orders remain disabled."
