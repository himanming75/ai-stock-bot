$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "ALPACA PAPER ONLY ARM"
Write-Host "This does NOT submit an order."
$Confirm=Read-Host "Type ARM_ALPACA_PAPER_ONLY"
if($Confirm -ne "ARM_ALPACA_PAPER_ONLY"){
 throw "PAPER ARM CANCELLED"
}

$Dir="C:\stock-bot\runtime\paper_autonomous_execution"
New-Item -ItemType Directory -Force $Dir | Out-Null

$Payload=[ordered]@{
 mode="PAPER_ONLY"
 armed=$true
 live_submission_enabled=$false
 armed_at_utc=[DateTime]::UtcNow.ToString("o")
}

$Payload | ConvertTo-Json | Set-Content `
 "$Dir\arm_token.json" -Encoding UTF8

Write-Host "PAPER_ONLY ARM TOKEN: READY"
Write-Host "LIVE SUBMISSION: FALSE"
