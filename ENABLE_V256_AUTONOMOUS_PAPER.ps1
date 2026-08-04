$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$policyPath = ".\release\v256_01_to_v260_64\config\autonomous_paper_policy.json"
$confirmPath = ".\release\v256_01_to_v260_64\control\autonomous_paper_confirmation.json"
$typed = Read-Host "Type ENABLE_AUTONOMOUS_PAPER to enable Alpaca Paper submission"
if($typed -ne "ENABLE_AUTONOMOUS_PAPER"){throw "Confirmation phrase did not match."}
$policy = Get-Content $policyPath -Raw | ConvertFrom-Json
$policy.autonomous_cycle_enabled = $true
$policy.real_paper_submission_enabled = $true
$policy | ConvertTo-Json -Depth 20 | Set-Content $policyPath -Encoding UTF8
@{
  enabled = $true
  phrase = "ENABLE_AUTONOMOUS_PAPER"
  updated_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content $confirmPath -Encoding UTF8
Write-Host "Autonomous Alpaca Paper submission ENABLED."
Write-Host "Live trading remains disabled."
