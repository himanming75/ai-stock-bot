from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p3_micro_paper.token import create_token, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ticket",
        default="release/p3_micro_paper/actual/p3_micro_ticket.json",
    )
    parser.add_argument(
        "--output",
        default="release/p3_micro_paper/actual/p3_micro_token.json",
    )
    args = parser.parse_args()

    digest = sha256_file(Path(args.ticket))
    token = create_token(Path(args.output), digest)

    print("P3 MICRO PAPER APPROVAL TOKEN CREATED")
    print("Nonce:", token["nonce"])
    print("Expires:", token["expires_at"])
    print("Ticket SHA256:", token["ticket_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
