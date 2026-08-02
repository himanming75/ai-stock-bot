from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.performance_collector import (
    PaperPilotPerformanceCollector,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--collect-snapshot", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = PaperPilotPerformanceCollector().run(
        policy_path=root/"release/op4_09_to_op4_12/input/paper_performance_policy.json",
        foundation_result_path=root/"release/op4_01_to_op4_04/actual/controlled_paper_pilot_foundation_result.json",
        session_monitor_result_path=root/"release/op4_05_to_op4_08/actual/paper_session_monitor_result.json",
        current_snapshot_path=root/"release/dash2_05/actual/current_paper_snapshot.json",
        trade_ledger_path=root/"release/op4_09_to_op4_12/input/paper_trade_performance_ledger.jsonl",
        equity_history_path=root/"release/op4_09_to_op4_12/actual/paper_equity_history.jsonl",
        daily_report_path=root/"release/op4_09_to_op4_12/actual/paper_daily_performance_report.json",
        performance_report_path=root/"release/op4_09_to_op4_12/actual/paper_pilot_performance_report.json",
        dashboard_state_path=root/"release/op4_09_to_op4_12/actual/paper_performance_dashboard_state.json",
        result_path=root/"release/op4_09_to_op4_12/actual/paper_performance_collector_result.json",
        collect_snapshot=args.collect_snapshot,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
