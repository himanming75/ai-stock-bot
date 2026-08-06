from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saas_foundation.service import (
    SaaSFoundationCertificationService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v7001_7200_saas_foundation/actual"
        ),
    )
    args = parser.parse_args()
    result = SaaSFoundationCertificationService().evaluate(
        output_dir=Path(args.output_dir)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
