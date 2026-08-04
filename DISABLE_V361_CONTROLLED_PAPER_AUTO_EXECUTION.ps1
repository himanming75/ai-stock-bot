$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Path=Join-Path $Root "release\v361_01_to_v370_64\config\controlled_paper_execution_policy.json"
$P=Get-Content $Path -Raw|ConvertFrom-Json;$P.paper_submission_enabled=$false;$P.kill_switch_active=$true
$P|ConvertTo-Json -Depth 20|Set-Content $Path -Encoding utf8
Write-Host "Controlled Paper submission disabled and kill switch activated."
