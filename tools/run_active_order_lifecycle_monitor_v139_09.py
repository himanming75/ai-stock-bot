from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.active_order_lifecycle_monitor import ActiveOrderLifecycleMonitor


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--acceptance-result-path", default="release/v139_08/actual/submitted_order_acceptance_verification_result.json")
    parser.add_argument("--acceptance-token-path", default="release/v139_08/actual/submitted_order_acceptance_token.json")
    parser.add_argument("--lifecycle-snapshot-path", default="release/v139_09/input/active_order_lifecycle_snapshot.json")
    parser.add_argument("--previous-lifecycle-snapshot-path", default="release/v139_09/actual/previous_active_order_lifecycle_snapshot.json")
    parser.add_argument("--monitor-state-path", default="release/v139_09/actual/active_order_monitor_state.json")
    parser.add_argument("--result-path", default="release/v139_09/actual/active_order_lifecycle_monitor_result.json")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    report = ActiveOrderLifecycleMonitor().run(
        acceptance_result_path=root / args.acceptance_result_path,
        acceptance_token_path=root / args.acceptance_token_path,
        lifecycle_snapshot_path=root / args.lifecycle_snapshot_path,
        previous_lifecycle_snapshot_path=root / args.previous_lifecycle_snapshot_path,
        monitor_state_path=root / args.monitor_state_path,
        result_path=root / args.result_path,
    )
    print(json.dumps(report.to_json_dict(), indent=2, sort_keys=True))
    print(f"RESULT_FILE={(root / args.result_path).resolve()}")
    return 0 if report.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
