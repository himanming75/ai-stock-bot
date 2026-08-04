import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from multi_broker_production.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V200.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"MULTI_BROKER_MULTI_ACCOUNT_PRODUCTION_READY","MULTI_BROKER_MULTI_ACCOUNT_REVIEW_REQUIRED"},
"multi_broker_ready":r["multi_broker_ready"] is True,
"multi_account_ready":r["multi_account_ready"] is True,
"all_snapshots_read_only":all(x["read_only"] is True for x in r["snapshots"]),
"all_order_support_disabled":all(x["supports_orders"] is False for x in r["snapshots"]),
"automatic_write_failover_disabled":r["automatic_write_failover_enabled"] is False,
"broker_write_disabled":r["broker_write_enabled"] is False,
"live_submission_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/multi_broker_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
"verification_stage":"V200.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r["state"],
"broker_health":r["broker_health"],
"portfolio_summary":r["unified_portfolio"]["summary"],
"failover":r["failover"],
"production_gate":r["production_gate"],
"actual_live_orders_submitted":0,
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v196_01_to_v200_64/actual/multi_broker_production_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
