from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from long_run_qualification.config import load, validate
from long_run_qualification.qualifier import qualify
policy = load(ROOT); validation = validate(policy); result = qualify(ROOT)
checks = {
 "policy_valid": validation["valid"],
 "allowed_state": result["state"] in {"REAL_PAPER_LONG_RUN_READY_BLOCKED","REAL_PAPER_LONG_RUN_QUALIFICATION_PENDING","REAL_PAPER_LONG_RUN_QUALIFIED"},
 "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
 "live_orders_zero": result["actual_live_orders_submitted"] == 0,
 "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
 "live_submission_disabled": policy.get("live_submission_enabled") is False,
 "broker_write_disabled": policy.get("broker_write_enabled") is False,
 "monitor_only": policy.get("monitor_only") is True,
}
out={"verification_stage":"V330.64","verification_status":"PASS" if all(checks.values()) else "FAIL","state":result["state"],"checks":checks,"failed":[k for k,v in checks.items() if not v]}
print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if all(checks.values()) else 1)
