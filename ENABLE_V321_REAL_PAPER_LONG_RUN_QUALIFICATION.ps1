$ErrorActionPreference = "Stop"
$Expected = "ENABLE_REAL_PAPER_LONG_RUN_QUALIFICATION"
$Typed = Read-Host "Type $Expected"
if ($Typed -ne $Expected) { Write-Error "Confirmation text did not match."; exit 1 }

$PolicyPath = Join-Path $PSScriptRoot "release\v321_01_to_v330_64\config\real_paper_long_run_policy.json"
if (-not (Test-Path $PolicyPath)) { throw "Policy file not found: $PolicyPath" }

$Policy = Get-Content $PolicyPath -Raw | ConvertFrom-Json
$Policy.qualification_enabled = $true
$Policy.paper_submission_enabled = $false
$Policy.live_submission_enabled = $false
$Policy.live_network_enabled = $false
$Policy.broker_write_enabled = $false
$Policy.monitor_only = $true
$Policy.maximum_new_orders_per_day = 0
$Policy.paper_base_url = "https://paper-api.alpaca.markets"

$Json = $Policy | ConvertTo-Json -Depth 20
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($PolicyPath, $Json + [Environment]::NewLine, $Utf8NoBom)

Write-Host "Real Paper long-run qualification enabled."
Write-Host "UTF-8 policy saved without BOM."
Write-Host "Monitor-only. New Paper and Live orders remain disabled."
