$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Path=Join-Path $Root "release\v361_01_to_v370_64\config\controlled_paper_execution_policy.json"
$C=Read-Host "Type ENABLE_CONTROLLED_PAPER_AUTO_EXECUTION"
if($C-ne"ENABLE_CONTROLLED_PAPER_AUTO_EXECUTION"){throw "Confirmation phrase did not match."}
$P=Get-Content $Path -Raw|ConvertFrom-Json;$P.paper_submission_enabled=$true;$P.kill_switch_active=$false
$P|ConvertTo-Json -Depth 20|Set-Content $Path -Encoding utf8
Write-Host "Controlled Paper policy enabled: SPY only, market/day, max `$1, max one order/day."
Write-Host "Live endpoint remains disabled."
