import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from real_paper_data_collection.collector import collect

r = collect(ROOT, allow_network=False)
checks = {
    "stage": r["stage"] == "V320.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {
        "REAL_PAPER_DATA_COLLECTION_ACTIVE",
        "REAL_PAPER_DATA_COLLECTION_READY_BLOCKED",
    },
    "collector_default_off": "COLLECTOR_DISABLED" in r["blocking_reasons"],
    "network_blocked": "NETWORK_NOT_AUTHORIZED" in r["blocking_reasons"],
    "monitor_only": r["checks"]["monitor_only"],
    "paper_submission_disabled": r["paper_submission_enabled"] is False,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
}
failed = [k for k, v in checks.items() if not v]
v = {
    "verification_stage": "V320.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
}
print(json.dumps(v, indent=2, sort_keys=True))
out = ROOT / "release/v311_01_to_v320_64/actual/real_paper_data_collection_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(v, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
