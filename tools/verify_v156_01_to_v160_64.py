import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from operations_manager.config import load,validate
from operations_manager.health import evaluate
from operations_manager.recovery import create_plan
c=load(ROOT);v=validate(c);h=evaluate(ROOT);r=create_plan(ROOT)
checks={
"config_valid":v["valid"],
"all_schedules_default_off":not any([c["web_controller_autostart_enabled"],c["pre_market_check_enabled"],c["intraday_shadow_enabled"],c["post_market_report_enabled"]]),
"scheduled_order_submission_disabled":c["automated_paper_submission_enabled"] is False,
"paper_only":c["paper_only"] is True,
"live_submission_disabled":c["live_submission_enabled"] is False,
"health_live_orders_zero":h["actual_live_orders_submitted"]==0,
"recovery_live_actions_absent":r["live_actions_included"] is False,
"operations_api_present":(ROOT/"web_controller/operations_api.py").exists(),
}
failed=[k for k,x in checks.items() if not x]
result={
"verification_stage":"V160.64",
"verification_status":"PASS" if not failed else "FAIL",
"controller_url":"http://127.0.0.1:8765",
"config":c,"health":h,"recovery":r,
"safety":{"scheduled_order_submission_enabled":False,"live_submission_enabled":False,"actual_live_orders_submitted":0},
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v156_01_to_v160_64/actual/operations_manager_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
