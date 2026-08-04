$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$PolicyPath=".\release\v121_01_to_v123_64\input\alpaca_paper_policy.json"
$Policy=Get-Content -LiteralPath $PolicyPath -Raw | ConvertFrom-Json

$Result=[ordered]@{
    project_path=(Get-Location).Path
    policy_found=(Test-Path -LiteralPath $PolicyPath)
    paper_mode=$Policy.paper_mode
    configured_real_network_enabled=$Policy.real_network_enabled
    configured_paper_submission_enabled=$Policy.paper_submission_enabled
    live_submission_enabled=$Policy.live_submission_enabled
    paper_key_present=(-not [string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_API_KEY))
    paper_secret_present=(-not [string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_SECRET_KEY))
    read_only_script_found=(Test-Path .\RUN_V121_TO_V123_REAL_READ_ONLY.ps1)
    paper_order_script_found=(Test-Path .\RUN_V121_TO_V123_SUBMIT_ONE_PAPER_ORDER.ps1)
}

$Result | ConvertTo-Json
