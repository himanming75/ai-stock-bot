from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from partial_fill_validation.service import (
    PartialFillValidationService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-seconds", type=int, default=10)
    parser.add_argument("--max-cycles", type=int, default=30)
    parser.add_argument(
        "--output-dir",
        default="release/partial_fill_validation/actual",
    )
    args = parser.parse_args()

    result = PartialFillValidationService().monitor(
        output_dir=Path(args.output_dir),
        interval_seconds=max(1, args.interval_seconds),
        max_cycles=max(1, args.max_cycles),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
