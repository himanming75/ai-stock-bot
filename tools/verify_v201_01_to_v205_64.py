import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from broker_plugins.engine import evaluate
r=evaluate(ROOT)
checks={
"stage":r["stage"]=="V205.64",
"status":r["status"]=="PASS",
"allowed_state":r["state"] in {"BROKER_PLUGIN_FRAMEWORK_READY","BROKER_PLUGIN_FRAMEWORK_REVIEW_REQUIRED"},
"plugins_discovered":r["discovered_plugin_count"]>=5,
"enabled_plugins_loadable":r["enabled_plugin_count"]==r["loadable_plugin_count"],
"all_read_only":all(x["read_only"] is True for x in r["plugins"]),
"orders_disabled":all(x["supports_orders"] is False for x in r["plugins"]),
"plugin_submission_disabled":r["plugin_order_submission_enabled"] is False,
"broker_write_disabled":r["broker_write_enabled"] is False,
"live_submission_disabled":r["live_submission_enabled"] is False,
"live_orders_zero":r["actual_live_orders_submitted"]==0,
"web_api_present":(ROOT/"web_controller/broker_plugins_api.py").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
"verification_stage":"V205.64",
"verification_status":"PASS" if not failed else "FAIL",
"state":r["state"],
"plugin_counts":{
"discovered":r["discovered_plugin_count"],
"enabled":r["enabled_plugin_count"],
"loadable":r["loadable_plugin_count"],
},
"plugins":r["plugins"],
"capability_matrix":r["capability_matrix"],
"reload_plan":r["reload_plan"],
"actual_live_orders_submitted":0,
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v201_01_to_v205_64/actual/broker_plugin_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
