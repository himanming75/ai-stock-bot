from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p3_cancel_validation.service import (
    P3PaperCancelValidationService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument(
        "--plan",
        default=(
            "release/p3_cancel_validation/actual/"
            "cancel_validation_plan.json"
        ),
    )
    parser.add_argument(
        "--token",
        default=(
            "release/p3_cancel_validation/actual/"
            "cancel_validation_token.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="release/p3_cancel_validation/actual",
    )
    parser.add_argument("--poll-interval-seconds", type=int, default=1)
    parser.add_argument("--max-poll-cycles", type=int, default=20)
    args = parser.parse_args()

    result = P3PaperCancelValidationService().run(
        plan_path=Path(args.plan),
        token_path=Path(args.token),
        nonce=args.nonce,
        output_dir=Path(args.output_dir),
        poll_interval_seconds=max(
            1, args.poll_interval_seconds
        ),
        max_poll_cycles=max(1, args.max_poll_cycles),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
