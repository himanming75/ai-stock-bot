from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_certification.service import (
    AutonomousPaperCertificationService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=str(ROOT))
    parser.add_argument(
        "--policy",
        default=(
            "release/v391_400_autonomous_paper_certification/"
            "config/certification_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v391_400_autonomous_paper_certification/actual"
        ),
    )
    args = parser.parse_args()

    result = AutonomousPaperCertificationService().evaluate(
        repository_root=Path(args.repository_root),
        policy_path=Path(args.policy),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
