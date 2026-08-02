from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.daily_read_only_observation import DailyReadOnlyObservation

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    a = p.parse_args()
    root = Path(a.repository_root).resolve()
    result = DailyReadOnlyObservation().run(
        pilot_result_path=root/"release/op1_01_to_op1_04/actual/paper_operations_pilot_result.json",
        current_snapshot_path=root/"release/op1_05_to_op1_08/input/current_paper_snapshot.json",
        previous_snapshot_path=root/"release/op1_05_to_op1_08/input/previous_paper_snapshot.json",
        observation_policy_path=root/"release/op1_05_to_op1_08/input/observation_policy.json",
        account_drift_path=root/"release/op1_05_to_op1_08/actual/account_drift_report.json",
        order_watch_path=root/"release/op1_05_to_op1_08/actual/open_order_watch_report.json",
        position_watch_path=root/"release/op1_05_to_op1_08/actual/position_watch_report.json",
        daily_report_path=root/"release/op1_05_to_op1_08/actual/daily_operations_report.json",
        observation_token_path=root/"release/op1_05_to_op1_08/actual/daily_observation_token.json",
        result_path=root/"release/op1_05_to_op1_08/actual/daily_read_only_observation_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
