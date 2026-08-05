from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gate_remediation_readiness.service import (
    GateRemediationReadinessService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=str(ROOT))
    parser.add_argument(
        "--policy",
        default=(
            "release/v381_390_gate_remediation_readiness/"
            "config/readiness_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v381_390_gate_remediation_readiness/actual"
        ),
    )
    args = parser.parse_args()

    result = GateRemediationReadinessService().evaluate(
        repository_root=Path(args.repository_root),
        output_dir=Path(args.output_dir),
        policy_path=Path(args.policy),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
