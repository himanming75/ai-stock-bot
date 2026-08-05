from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_watchdog.service import AutomationWatchdog

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default=(
            "release/automation_watchdog_restart_recovery/"
            "config/watchdog_policy.json"
        ),
    )
    parser.add_argument("--max-watch-cycles", type=int, default=2)
    args = parser.parse_args()

    result = AutomationWatchdog(ROOT).run(
        policy_path=Path(args.policy),
        max_watch_cycles=max(1, args.max_watch_cycles),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS", "IDLE"} else 2

if __name__ == "__main__":
    raise SystemExit(main())
