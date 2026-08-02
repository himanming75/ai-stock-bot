from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.scheduled_runtime_bundle import ScheduledRuntimeBundle

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    result = ScheduledRuntimeBundle().run(
        runtime_result_path=root/"release/v142_01_to_v142_04/actual/autonomous_paper_runtime_result.json",
        runtime_token_path=root/"release/v142_01_to_v142_04/actual/autonomous_paper_runtime_token.json",
        schedule_policy_path=root/"release/v142_05_to_v142_08/input/schedule_policy.json",
        resume_snapshot_path=root/"release/v142_05_to_v142_08/input/session_resume_snapshot.json",
        recovery_snapshot_path=root/"release/v142_05_to_v142_08/input/automatic_recovery_snapshot.json",
        emergency_stop_path=root/"release/v142_01_to_v142_04/input/emergency_stop.json",
        scheduled_state_path=root/"release/v142_05_to_v142_08/actual/scheduled_runtime_state.json",
        heartbeat_path=root/"release/v142_05_to_v142_08/actual/scheduled_runtime_heartbeat.json",
        recovery_token_path=root/"release/v142_05_to_v142_08/actual/automatic_recovery_token.json",
        scheduled_token_path=root/"release/v142_05_to_v142_08/actual/scheduled_runtime_token.json",
        result_path=root/"release/v142_05_to_v142_08/actual/scheduled_runtime_bundle_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
