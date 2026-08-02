from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_pilot.session_monitor import (
    PaperPilotSessionMonitor,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--write-heartbeat",
        action="store_true",
    )
    parser.add_argument(
        "--controlled-stop",
        action="store_true",
    )
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = PaperPilotSessionMonitor().run(
        policy_path=root/"release/op4_05_to_op4_08/input/paper_session_monitor_policy.json",
        foundation_result_path=root/"release/op4_01_to_op4_04/actual/controlled_paper_pilot_foundation_result.json",
        pilot_lock_path=root/"release/op4_01_to_op4_04/actual/paper_pilot.lock.json",
        pilot_session_path=root/"release/op4_01_to_op4_04/actual/paper_pilot_session.json",
        heartbeat_path=root/"release/op4_05_to_op4_08/actual/paper_pilot_heartbeat.json",
        health_path=root/"release/op4_05_to_op4_08/actual/paper_session_health.json",
        controlled_stop_path=root/"release/op4_05_to_op4_08/actual/paper_session_controlled_stop.json",
        dashboard_state_path=root/"release/op4_05_to_op4_08/actual/paper_session_monitor_dashboard_state.json",
        result_path=root/"release/op4_05_to_op4_08/actual/paper_session_monitor_result.json",
        write_heartbeat=args.write_heartbeat,
        request_controlled_stop=args.controlled_stop,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
