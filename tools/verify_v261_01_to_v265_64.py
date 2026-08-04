import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_session.runner import run

def fake_cycle(root: Path, allow_network: bool) -> dict:
    return {
        "state": "VERIFY_FAKE",
        "market_open": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }

result = run(ROOT, fake_cycle, allow_network=False, sleep_enabled=False)
checks = {
    "stage": result["stage"] == "V265.64",
    "status": result["status"] == "PASS",
    "allowed_state": result["state"] in {
        "AUTONOMOUS_PAPER_SESSION_READY_BLOCKED",
        "AUTONOMOUS_PAPER_SESSION_COMPLETE",
    },
    "default_runner_disabled": "SESSION_RUNNER_DISABLED" in result["blocking_reasons"],
    "network_not_authorized": "NETWORK_NOT_AUTHORIZED_FOR_SESSION" in result["blocking_reasons"],
    "cycles_zero": result["cycle_count"] == 0,
    "paper_orders_zero": result["paper_orders_submitted"] == 0,
    "live_orders_zero": result["actual_live_orders_submitted"] == 0,
    "checkpoint_present": (
        ROOT / "release/v261_01_to_v265_64/actual/session_checkpoint.json"
    ).exists(),
    "web_api_present": (
        ROOT / "web_controller/autonomous_paper_session_api.py"
    ).exists(),
}
failed = [name for name, passed in checks.items() if not passed]
verification = {
    "verification_stage": "V265.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": result["state"],
    "checks": checks,
    "failed": failed,
    "blocking_reasons": result["blocking_reasons"],
    "actual_paper_orders_submitted": result["paper_orders_submitted"],
    "actual_live_orders_submitted": 0,
}
print(json.dumps(verification, indent=2, sort_keys=True))
output = ROOT / "release/v261_01_to_v265_64/actual/session_runner_verification.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
