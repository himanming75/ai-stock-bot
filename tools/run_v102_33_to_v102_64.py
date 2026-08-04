from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_decision.engine import evaluate

def main() -> int:
    result = evaluate(ROOT)
    decision = result.get("autonomous_decision", {})
    confidence = result.get("confidence", {})
    summary = {
        "stage": result.get("stage"),
        "state": result.get("state"),
        "status": result.get("status"),
        "decision_id": result.get("decision_id"),
        "decision": decision.get("decision"),
        "reason": decision.get("reason"),
        "confidence_score": confidence.get("confidence_score"),
        "confidence_level": confidence.get("confidence_level"),
        "conflict_count": result.get("conflict_analysis", {}).get("conflict_count"),
        "veto_count": result.get("safety_veto", {}).get("veto_count"),
        "actionable_adjustment_count": result.get("signals", {}).get(
            "actionable_adjustment_count"
        ),
        "approval_eligible": result.get("approval_gate", {}).get(
            "approval_eligible"
        ),
        "manual_approval_required": result.get("manual_approval_required"),
        "execution_authorized": result.get("execution_authorized"),
        "actual_orders_submitted": result.get("actual_orders_submitted"),
        "paper_only": result.get("paper_only"),
        "next_phase": result.get("next_phase"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT / "release/v102_33_to_v102_64/actual/"
                "autonomous_decision_result.json"
            ).resolve()
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
