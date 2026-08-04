import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from final_production_release.engine import evaluate
r=evaluate(ROOT,create_release_bundle=False)
checks={
 "stage":r["stage"]=="V220.64",
 "status":r["status"]=="PASS",
 "allowed_state":r["state"] in {"V220_FINAL_PRODUCTION_RELEASE_COMPLETE","V220_FINAL_PRODUCTION_RELEASE_REVIEW_REQUIRED"},
 "paper_ready":r["paper_trading_ready"] is True,
 "live_not_auto_ready":r["live_trading_ready"] is False,
 "manual_live_activation_required":r["manual_live_activation_required"] is True,
 "automatic_strategy_promotion_disabled":r["automatic_strategy_promotion_enabled"] is False,
 "automatic_submission_disabled":r["automatic_order_submission_enabled"] is False,
 "broker_write_disabled":r["broker_write_enabled"] is False,
 "live_submission_disabled":r["live_submission_enabled"] is False,
 "live_network_write_disabled":r["live_network_write_enabled"] is False,
 "live_orders_zero":r["actual_live_orders_submitted"]==0,
 "web_api_present":(ROOT/"web_controller/final_release_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
 "verification_stage":"V220.64",
 "verification_status":"PASS" if not failed else "FAIL",
 "state":r["state"],
 "final_release_ready":r["final_release_ready"],
 "inventory_summary":{
   "present_stage_count":r["inventory"]["present_stage_count"],
   "expected_stage_count":r["inventory"]["expected_stage_count"],
   "missing_stages":r["inventory"]["missing_stages"],
 },
 "integration_summary":{
   "present_module_count":r["integration"]["present_module_count"],
   "module_count":r["integration"]["module_count"],
   "all_required_files_present":r["integration"]["all_required_files_present"],
 },
 "certificate":r["certificate"],
 "actual_live_orders_submitted":r["actual_live_orders_submitted"],
 "checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v216_01_to_v220_64/actual/v220_final_production_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
