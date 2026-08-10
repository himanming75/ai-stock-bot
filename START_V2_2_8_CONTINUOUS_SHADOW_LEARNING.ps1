$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo

Write-Host "V2.2.8 CONTINUOUS AI SHADOW LEARNING COLLECTOR"
Write-Host "Watches existing canonical shadow + completed Paper trade ledger."
Write-Host "Does NOT start the Paper trading engine."
Write-Host "Broker network from V2.2.8: OFF"
Write-Host "Paper orders from V2.2.8: 0"
Write-Host "Live trading: LOCKED"
Write-Host ""
$confirm=Read-Host "Type RUN_CONTINUOUS_AI_SHADOW_LEARNING"
if($confirm -ne "RUN_CONTINUOUS_AI_SHADOW_LEARNING"){
    throw "CONFIRMATION MISMATCH"
}

$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" -m ai_engine_v2.continuous_shadow_learning_pipeline_cli_v2_2_8 `
 --root $Repo `
 --mode continuous `
 --poll-seconds 60 `
 --max-runtime-seconds 28800
if($LASTEXITCODE -ne 0){throw "V2.2.8 CONTINUOUS COLLECTOR FAILED"}
