from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.pilot_foundation import (
    ControlledPaperPilotFoundation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--start-pilot",
        action="store_true",
    )
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = ControlledPaperPilotFoundation().run(
        policy_path=root/"release/op4_01_to_op4_04/input/paper_pilot_policy.json",
        current_snapshot_path=root/"release/dash2_05/actual/current_paper_snapshot.json",
        lifecycle_result_path=root/"release/op3_09_to_op3_12/actual/paper_order_lifecycle_result.json",
        limited_runtime_result_path=root/"release/op3_13_to_op3_16/actual/limited_autonomous_paper_trading_result.json",
        pilot_registry_path=root/"release/op4_01_to_op4_04/actual/paper_pilot_registry.json",
        pilot_lock_path=root/"release/op4_01_to_op4_04/actual/paper_pilot.lock.json",
        pilot_session_path=root/"release/op4_01_to_op4_04/actual/paper_pilot_session.json",
        dashboard_state_path=root/"release/op4_01_to_op4_04/actual/paper_pilot_dashboard_state.json",
        result_path=root/"release/op4_01_to_op4_04/actual/controlled_paper_pilot_foundation_result.json",
        start_pilot=args.start_pilot,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
