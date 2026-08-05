
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[1]
r = json.loads((ROOT/"release/v460_64/actual/paper_broker_integration_audit.json").read_text(encoding="utf-8-sig"))
checks = {
 "stage": r.get("stage") == "V460.64",
 "status": r.get("status") == "PASS",
 "features_present": isinstance(r.get("features"), dict) and len(r["features"]) >= 30,
 "audit_hash": len(str(r.get("audit_hash",""))) == 64,
 "scope_present": isinstance(r.get("next_bundle_scope"), dict),
 "no_omitted_features": r.get("next_bundle_scope",{}).get("mandatory_features_omitted") == [],
 "network_off": r.get("network_used") is False,
 "credentials_off": r.get("broker_credentials_used") is False,
 "broker_write_off": r.get("broker_write_enabled") is False,
 "paper_submission_off": r.get("paper_submission_enabled") is False,
 "live_submission_off": r.get("live_submission_enabled") is False,
 "paper_orders_zero": r.get("actual_paper_orders_submitted") == 0,
 "live_orders_zero": r.get("actual_live_orders_submitted") == 0,
}
out={"verification_stage":"V460.64","verification_status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"failed":[k for k,v in checks.items() if not v]}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
