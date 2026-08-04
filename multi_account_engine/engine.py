from datetime import datetime,timezone
from pathlib import Path
from multi_account_engine.config import load,validate
from multi_account_engine.conflicts import resolve
from multi_account_engine.credentials import detect
from multi_account_engine.io import load_json,write_json,append_jsonl
from multi_account_engine.risk import evaluate as risk_eval
from multi_account_engine.routing import route
def evaluate(root):
 root=Path(root); p=load(root); val=validate(p)
 s=load_json(root/"release/v271_01_to_v280_64/actual/multi_timeframe_strategy_result.json") or load_json(root/"release/v281_01_to_v290_64/input/multi_account_strategy_fixture.json")
 snaps=load_json(root/"release/v281_01_to_v290_64/input/multi_account_snapshots.json").get("accounts",{})
 accts=p.get("accounts",[]); creds={a["account_id"]:detect(a) for a in accts}; risks={a["account_id"]:risk_eval(a,snaps.get(a["account_id"],{})) for a in accts}
 routes=resolve(route(s.get("strategy_rows",[]),accts),bool(p.get("allow_cross_account_symbol_overlap")))
 rows=[]
 for a in accts:
  aid=a["account_id"]; rows.append({"account_id":aid,"broker":a["broker"],"environment":a["environment"],"assigned_profiles":a["assigned_profiles"],"capital_limit":a["capital_limit"],"credential_state":creds[aid],"risk_state":risks[aid],"routes":[r for r in routes if r["account_id"]==aid],"account_enabled":a.get("enabled") is True,"paper_submission_authorized":False,"live_submission_authorized":False})
 c={"policy_valid":val["valid"],"accounts_present":bool(accts),"routes_present":bool(routes),"all_accounts_paper":all(a.get("environment")=="PAPER" for a in accts),"paper_read_disabled":p.get("paper_read_enabled") is False,"paper_submission_disabled":p.get("paper_submission_enabled") is False,"live_submission_disabled":p.get("live_submission_enabled") is False,"live_network_disabled":p.get("live_network_enabled") is False,"broker_write_disabled":p.get("broker_write_enabled") is False}
 f=[k for k,v in c.items() if not v]; state="MULTI_ACCOUNT_ENGINE_READY" if not f else "MULTI_ACCOUNT_ENGINE_REVIEW_REQUIRED"
 r={"stage":"V290.64","state":state,"status":"PASS","observed_at":datetime.now(timezone.utc).isoformat(),"accounts":rows,"routes":routes,"checks":c,"failed":f,"paper_read_enabled":False,"paper_submission_enabled":False,"live_submission_enabled":False,"live_network_enabled":False,"broker_write_enabled":False,"actual_paper_orders_submitted":0,"actual_live_orders_submitted":0,"next_phase":"V291_01_TO_V300_64_PAPER_QUALIFICATION_AND_BROKER_RECONCILIATION"}
 act=root/"release/v281_01_to_v290_64/actual"; write_json(act/"multi_account_engine_result.json",r); write_json(act/"multi_account_routes.json",{"rows":routes}); write_json(act/"multi_account_risk_states.json",risks); append_jsonl(act/"multi_account_engine_ledger.jsonl",{"observed_at":r["observed_at"],"state":state,"account_count":len(accts),"route_count":len(routes),"actual_live_orders_submitted":0}); return r
