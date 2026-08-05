from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_account_framework.service import (
    MultiAccountFrameworkService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default=(
            "release/v431_460_multi_account_framework/"
            "config/account_registry.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v431_460_multi_account_framework/"
            "config/multi_account_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v431_460_multi_account_framework/actual"
        ),
    )
    args = parser.parse_args()

    result = MultiAccountFrameworkService().evaluate(
        registry_path=Path(args.registry),
        policy_path=Path(args.policy),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
