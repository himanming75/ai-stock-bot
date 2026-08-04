import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from real_paper_validation.engine import evaluate

r = evaluate(ROOT, allow_network=False)
checks = {
    "stage": r["stage"] == "V305.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {"REAL_PAPER_READ_VALIDATED", "REAL_PAPER_VALIDATION_READY_BLOCKED"},
    "network_blocked": "NETWORK_NOT_AUTHORIZED" in r["blocking_reasons"],
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "live_submission_disabled": r["live_submission_enabled"] is False,
}
failed = [k for k, v in checks.items() if not v]
v = {"verification_stage":"V305.64","verification_status":"PASS" if not failed else "FAIL","checks":checks,"failed":failed,"state":r["state"]}
print(json.dumps(v, indent=2, sort_keys=True))
(ROOT / "release/v301_01_to_v305_64/actual").mkdir(parents=True, exist_ok=True)
(ROOT / "release/v301_01_to_v305_64/actual/real_paper_validation_verification.json").write_text(json.dumps(v, indent=2)+"\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
