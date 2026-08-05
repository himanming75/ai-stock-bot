from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system_health_monitoring.service import (
    SystemHealthMonitoringService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=str(ROOT))
    parser.add_argument(
        "--policy",
        default=(
            "release/v351_360_system_health_monitoring/"
            "config/health_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v351_360_system_health_monitoring/actual"
        ),
    )
    args = parser.parse_args()

    result = SystemHealthMonitoringService().evaluate(
        repository_root=Path(args.repository_root),
        output_dir=Path(args.output_dir),
        policy_path=Path(args.policy),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    # Health FAIL is evidence, not an installer failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
