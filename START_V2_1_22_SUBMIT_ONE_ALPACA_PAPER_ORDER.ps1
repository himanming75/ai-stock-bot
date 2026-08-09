$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "V2.1.22 ONE BOUNDED ALPACA PAPER ORDER"
Write-Host "Paper account only. Maximum notional $25."
Write-Host "This command CAN submit one Alpaca Paper order if every guard passes."
$Confirm=Read-Host "Type SUBMIT_ALPACA_PAPER_ONCE"
if($Confirm -ne "SUBMIT_ALPACA_PAPER_ONCE"){
 throw "PAPER SUBMISSION CANCELLED"
}

$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.alpaca_paper_bounded_execution_cli_v2_1_22 `
 --root C:\stock-bot `
 --submit-paper `
 --confirmation SUBMIT_ALPACA_PAPER_ONCE
