$ErrorActionPreference='Stop'; Set-Location C:\stock-bot
$Py=if(Test-Path '.\.venv\Scripts\python.exe'){'.\.venv\Scripts\python.exe'}else{'python'}
& $Py -m unittest tests.test_runtime_observation_gate_v2_9_4 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $Py -m py_compile .\paper_daily_session\runner.py .\tools\certify_runtime_shadow_v2_9.py .\tools\certify_runtime_observation_gate_v2_9_4.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$r=Get-Content .\runtime\regime_aware_buy_shadow_v2_9_4\latest_runtime_observation_gate_v2_9_4.json -Raw|ConvertFrom-Json
if($r.status -like 'BLOCKED*'){throw "V2.9.4 BLOCKED: $($r.status)"}
Write-Host "VERIFY: PASS - $($r.status) - hooks $($r.successful_hook_count)/$($r.required_successful_hooks)"
