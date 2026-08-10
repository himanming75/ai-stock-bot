$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
& "$Repo\.venv\Scripts\python.exe" `
 -m broker_integration_v1.eligibility_block_reason_diagnostic_cli_v2_1_31_3 `
 --root $Repo --mode run
if($LASTEXITCODE -ne 0){throw "V2.1.31.3 DIAGNOSTIC FAILED"}
