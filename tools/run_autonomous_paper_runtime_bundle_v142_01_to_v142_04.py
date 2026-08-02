from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.autonomous_paper_runtime_bundle import (
    AutonomousPaperRuntimeBundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = AutonomousPaperRuntimeBundle().run(
        release_result_path=root/"release/v141_06_to_v141_08/actual/final_validation_release_result.json",
        release_token_path=root/"release/v141_06_to_v141_08/actual/paper_production_release_token.json",
        runtime_policy_path=root/"release/v142_01_to_v142_04/input/runtime_policy.json",
        watchdog_snapshot_path=root/"release/v142_01_to_v142_04/input/watchdog_snapshot.json",
        emergency_stop_path=root/"release/v142_01_to_v142_04/input/emergency_stop.json",
        runtime_lock_path=root/"release/v142_01_to_v142_04/actual/autonomous_runtime_lock.json",
        heartbeat_path=root/"release/v142_01_to_v142_04/actual/autonomous_runtime_heartbeat.json",
        tick_result_path=root/"release/v142_01_to_v142_04/actual/autonomous_runtime_tick_result.json",
        runtime_token_path=root/"release/v142_01_to_v142_04/actual/autonomous_paper_runtime_token.json",
        result_path=root/"release/v142_01_to_v142_04/actual/autonomous_paper_runtime_result.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
