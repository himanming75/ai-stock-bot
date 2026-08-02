from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.multi_day_validation import (
    MultiDayPaperValidationFoundation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--record-validation-day",
        action="store_true",
    )
    parser.add_argument("--validation-date", default="")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = MultiDayPaperValidationFoundation().run(
        policy_path=root/"release/op5_01_to_op5_04/input/multi_day_validation_policy.json",
        foundation_result_path=root/"release/op4_01_to_op4_04/actual/controlled_paper_pilot_foundation_result.json",
        session_result_path=root/"release/op4_05_to_op4_08/actual/paper_session_monitor_result.json",
        performance_result_path=root/"release/op4_09_to_op4_12/actual/paper_performance_collector_result.json",
        risk_result_path=root/"release/op4_13_to_op4_16/actual/paper_risk_monitor_result.json",
        automation_result_path=root/"release/op4_17_to_op4_20/actual/paper_pilot_automation_result.json",
        validation_ledger_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_ledger.jsonl",
        daily_record_path=root/"release/op5_01_to_op5_04/actual/latest_validation_day.json",
        validation_summary_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_summary.json",
        validation_gate_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_gate.json",
        dashboard_state_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_dashboard_state.json",
        result_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_result.json",
        record_validation_day=args.record_validation_day,
        validation_date=args.validation_date or None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
