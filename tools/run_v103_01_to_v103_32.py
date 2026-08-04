from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_cycle.engine import evaluate

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle-date", default=None)
    args = parser.parse_args()

    result = evaluate(ROOT, cycle_date=args.cycle_date)
    summary = {
        "stage": result.get("stage"),
        "state": result.get("state"),
        "status": result.get("status"),
        "cycle_id": result.get("cycle_id"),
        "cycle_date": result.get("cycle_date"),
        "source_decision": result.get("source_decision"),
        "cycle_action": result.get("cycle_action"),
        "completed_step_count": result.get("completed_step_count"),
        "failed_steps": result.get("failed_steps"),
        "duplicate_cycle": result.get("duplicate", {}).get("duplicate_cycle"),
        "checkpoint_generation": result.get("checkpoint", {}).get("generation"),
        "approval_eligible": result.get("approval_eligible"),
        "approval_granted": result.get("approval_granted"),
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
                ROOT / "release/v103_01_to_v103_32/actual/"
                "autonomous_cycle_result.json"
            ).resolve()
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
