from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.validation_analytics import MultiDayValidationAnalytics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = MultiDayValidationAnalytics().run(
        policy_path=root/"release/op5_05_to_op5_08/input/validation_analytics_policy.json",
        validation_summary_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_summary.json",
        validation_gate_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_gate.json",
        validation_ledger_path=root/"release/op5_01_to_op5_04/actual/multi_day_validation_ledger.jsonl",
        analytics_path=root/"release/op5_05_to_op5_08/actual/validation_analytics.json",
        trend_path=root/"release/op5_05_to_op5_08/actual/validation_trend.json",
        report_path=root/"release/op5_05_to_op5_08/actual/validation_analytics_report.json",
        dashboard_state_path=root/"release/op5_05_to_op5_08/actual/validation_analytics_dashboard_state.json",
        result_path=root/"release/op5_05_to_op5_08/actual/validation_analytics_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
