from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tools.multi_order_continuation_stress_v77_8 import digest, load_json, summary

def verify_output(output_dir: Path) -> dict:
    result = load_json(output_dir/"multi_order_continuation_stress_verification_v77_8.json")
    saved = load_json(output_dir/"multi_order_continuation_stress_summary_v77_8.json")
    errors = []
    expected = digest({k:v for k,v in result.items()
                       if k not in {"verification_sha256","issued_at_utc"}})
    if result.get("verification_sha256") != expected: errors.append("self-hash mismatch")
    if saved != summary(result): errors.append("summary mismatch")
    vr = result.get("verification_result", {})
    sr = result.get("stress_report", {})
    for key, value in sr.get("checks", {}).items():
        if value is not True: errors.append(f"stress check failed: {key}")
    validations = (
        (result.get("status") == "PASS", "status"),
        (sr.get("status") == "PASS", "stress status"),
        (sr.get("submitted_order_count") == 8, "order count"),
        (sr.get("applied_fill_count") == 12, "fill count"),
        (sr.get("duplicate_rejection_count") == 2, "duplicate count"),
        (vr.get("failed_gate_count") == 0, "failed gates"),
        (result.get("network_allowed") is False, "network"),
        (result.get("actual_orders_submitted") == 0, "actual orders"),
        (result.get("next_phase") == "V77_9_FAILURE_INJECTION_RECOVERY", "next phase"),
    )
    for passed, name in validations:
        if not passed: errors.append(name)
    return {
        "verified": not errors, "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors), "errors": errors,
        "multi_order_continuation_stress_sha256":
            result.get("multi_order_continuation_stress_sha256"),
        "stressed_state_sha256": sr.get("stressed_state_sha256"),
        "verification_sha256": result.get("verification_sha256"),
        "next_phase": result.get("next_phase"),
    }

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", required=True)
    r=verify_output(Path(p.parse_args().output_dir)); print(json.dumps(r, indent=2))
    return 0 if r["verified"] else 1

if __name__ == "__main__": raise SystemExit(main())
