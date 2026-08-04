from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_paper_runner.engine import evaluate

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-date", default=None)
    args = parser.parse_args()

    result = evaluate(ROOT, session_date=args.session_date)
    report = result.get("daily_report", {})
    summary = {
        "stage": result.get("stage"),
        "state": result.get("state"),
        "status": result.get("status"),
        "run_id": result.get("run_id"),
        "session_id": report.get("session_id"),
        "session_date": report.get("session_date"),
        "preflight_passed": report.get("preflight_passed"),
        "paper_simulation_authorized": result.get(
            "paper_simulation_authorized"
        ),
        "planned_strategy_count": report.get("planned_strategy_count"),
        "authorized_plan_count": report.get("authorized_plan_count"),
        "paper_plans_processed": result.get("paper_plans_processed"),
        "live_execution_authorized": result.get(
            "live_execution_authorized"
        ),
        "actual_orders_submitted": result.get("actual_orders_submitted"),
        "paper_only": result.get("paper_only"),
        "next_phase": result.get("next_phase"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT / "release/v106_01_to_v106_32/actual/"
                "daily_paper_runner_result.json"
            ).resolve()
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
