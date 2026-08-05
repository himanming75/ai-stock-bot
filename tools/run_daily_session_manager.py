from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_session_manager.service import DailySessionManager


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default=(
            "release/daily_session_manager_startup_autorun/"
            "config/daily_session_policy.json"
        ),
    )
    parser.add_argument(
        "--execute-watchdog",
        action="store_true",
    )
    args = parser.parse_args()

    result = DailySessionManager(ROOT).evaluate(
        policy_path=Path(args.policy),
        execute_watchdog=args.execute_watchdog,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
