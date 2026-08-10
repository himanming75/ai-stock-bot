$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo

Write-Host "V2.2.7 LOCAL SHADOW CAPTURE + SIMULATION"
Write-Host "Step 1: refresh V2.2.1 feature snapshot from existing canonical shadow"
Write-Host "Step 2: refresh V2.2.5 Champion/Challenger comparison"
Write-Host "Step 3: run V2.2.7 pure-local shadow simulator"
Write-Host "Broker orders from this workflow: NONE"
Write-Host "Live trading: LOCKED"

powershell -NoProfile -ExecutionPolicy Bypass `
 -File .\RUN_AI_TRADING_ENGINE_V2_2_1.ps1
if($LASTEXITCODE -ne 0){throw "V2.2.1 REFRESH FAILED"}

powershell -NoProfile -ExecutionPolicy Bypass `
 -File .\RUN_AI_TRADING_ENGINE_V2_2_5.ps1
if($LASTEXITCODE -ne 0){throw "V2.2.5 REFRESH FAILED"}

powershell -NoProfile -ExecutionPolicy Bypass `
 -File .\RUN_AI_TRADING_ENGINE_V2_2_7.ps1
if($LASTEXITCODE -ne 0){throw "V2.2.7 SIMULATION FAILED"}
