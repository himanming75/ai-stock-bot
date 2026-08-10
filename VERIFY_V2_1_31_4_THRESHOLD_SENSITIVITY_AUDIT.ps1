$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_threshold_sensitivity_shadow_audit_v2_1_31_4.py
if($LASTEXITCODE -ne 0){throw "V2.1.31.4 TEST FAILED"}

& $Python -c "from broker_integration_v1.threshold_sensitivity_shadow_audit_status_v2_1_31_4 import build_v2_1_31_4_status as f; s=f(); assert s['status']=='PASS_DEVELOPMENT_COMPLETE'; assert s['threshold_grid']==[0.60,0.65,0.70,0.75]; assert s['reward_risk_fixed']==1.0; assert s['horizons']==[5,15,30,60]; assert not s['broker_fill_pnl_fabricated']; assert s['current_execution_threshold']==0.75; assert not s['execution_threshold_modified']; assert not s['selector_modified']; assert not s['broker_network']; assert s['orders']==0; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "V2.1.31.4 VERIFY FAILED"}
