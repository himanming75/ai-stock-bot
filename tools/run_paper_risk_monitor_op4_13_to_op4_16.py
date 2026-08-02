from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.risk_monitor import PaperPilotRiskMonitor


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = PaperPilotRiskMonitor().run(
        policy_path=root/"release/op4_13_to_op4_16/input/paper_risk_policy.json",
        foundation_result_path=root/"release/op4_01_to_op4_04/actual/controlled_paper_pilot_foundation_result.json",
        session_monitor_result_path=root/"release/op4_05_to_op4_08/actual/paper_session_monitor_result.json",
        performance_result_path=root/"release/op4_09_to_op4_12/actual/paper_performance_collector_result.json",
        current_snapshot_path=root/"release/dash2_05/actual/current_paper_snapshot.json",
        drawdown_report_path=root/"release/op4_13_to_op4_16/actual/paper_drawdown_report.json",
        exposure_report_path=root/"release/op4_13_to_op4_16/actual/paper_exposure_report.json",
        daily_loss_report_path=root/"release/op4_13_to_op4_16/actual/paper_daily_loss_report.json",
        emergency_stop_gate_path=root/"release/op4_13_to_op4_16/actual/paper_emergency_stop_gate.json",
        dashboard_state_path=root/"release/op4_13_to_op4_16/actual/paper_risk_dashboard_state.json",
        result_path=root/"release/op4_13_to_op4_16/actual/paper_risk_monitor_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
