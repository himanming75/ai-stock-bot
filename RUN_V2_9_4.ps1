$ErrorActionPreference='Stop'; Set-Location C:\stock-bot
Write-Host '=== V2.9.4 NEXT SCHEDULED RUNTIME OBSERVATION GATE ==='
$Py=if(Test-Path '.\.venv\Scripts\python.exe'){'.\.venv\Scripts\python.exe'}else{'python'}
& $Py .\tools\certify_runtime_observation_gate_v2_9_4.py --root C:\stock-bot
exit $LASTEXITCODE
