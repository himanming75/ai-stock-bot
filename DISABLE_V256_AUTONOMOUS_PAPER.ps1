$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$policyPath = ".\release\v256_01_to_v260_64\config\autonomous_paper_policy.json"
$confirmPath = ".\release\v256_01_to_v260_64\control\autonomous_paper_confirmation.json"
$policy = Get-Content $policyPath -Raw | ConvertFrom-Json
$policy.autonomous_cycle_enabled = $false
$policy.real_paper_submission_enabled = $false
$policy | ConvertTo-Json -Depth 20 | Set-Content $policyPath -Encoding UTF8
@{enabled=$false;phrase="";updated_at=(Get-Date).ToUniversalTime().ToString("o")} |
 ConvertTo-Json | Set-Content $confirmPath -Encoding UTF8
Write-Host "Autonomous Alpaca Paper submission DISABLED."
