import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from web_controller.state import build_dashboard
d=build_dashboard(ROOT)
checks={
"v140_present":d.get("release",{}).get("state")!="NOT_AVAILABLE",
"emergency_stop_present":isinstance(d.get("emergency_stop"),dict),
"emergency_stop_default_on":d.get("emergency_stop",{}).get("enabled") is True,
"local_bind_only":d.get("safety",{}).get("local_bind_only") is True,
"live_network_disabled":d.get("safety",{}).get("live_network_enabled") is False,
"live_submission_disabled":d.get("safety",{}).get("live_submission_enabled") is False,
"live_orders_zero":d.get("safety",{}).get("actual_live_orders_submitted")==0,
"static_index":(ROOT/"web_controller/static/index.html").exists(),
}
failed=[k for k,v in checks.items() if not v]
result={
"verification_stage":"V145.64",
"verification_status":"PASS" if not failed else "FAIL",
"controller_url":"http://127.0.0.1:8765",
"release":d.get("release"),
"emergency_stop":d.get("emergency_stop"),
"safety":d.get("safety"),
"checks":checks,"failed":failed,
}
print(json.dumps(result,indent=2,sort_keys=True))
out=ROOT/"release/v141_01_to_v145_64/actual/web_controller_verification.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raise SystemExit(0 if not failed else 1)
