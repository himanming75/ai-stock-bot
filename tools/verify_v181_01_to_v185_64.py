import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from portfolio_broker.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V185.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"PORTFOLIO_BROKER_ADAPTER_FOUNDATION_READY","PORTFOLIO_BROKER_ADAPTER_REVIEW_REQUIRED"},
"multi_account_ready":r["multi_account_ready"] is True,
"adapter_foundation_ready":r["broker_adapter_foundation_ready"] is True,
"all_adapters_read_only":all(x["read_only"] is True for x in r["registered_brokers"]),
"all_adapters_no_orders":all(x["supports_orders"] is False for x in r["registered_brokers"]),
"broker_write_disabled":r["broker_write_enabled"] is False,
"live_submission_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/portfolio_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
"verification_stage":"V185.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r["state"],
"registered_brokers":r["registered_brokers"],
"portfolio_summary":r["portfolio"]["summary"],
"portfolio_risk_gate":r["portfolio_risk_gate"],
"actual_live_orders_submitted":0,
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v181_01_to_v185_64/actual/portfolio_broker_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
