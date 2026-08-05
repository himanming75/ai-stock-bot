from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p3_cancel_validation.token import create_token, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plan",
        default=(
            "release/p3_cancel_validation/actual/"
            "cancel_validation_plan.json"
        ),
    )
    parser.add_argument(
        "--output",
        default=(
            "release/p3_cancel_validation/actual/"
            "cancel_validation_token.json"
        ),
    )
    args = parser.parse_args()

    digest = sha256_file(Path(args.plan))
    token = create_token(Path(args.output), digest)

    print("P3 CANCEL APPROVAL TOKEN CREATED")
    print("Nonce:", token["nonce"])
    print("Expires:", token["expires_at"])
    print("Plan SHA256:", token["plan_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
