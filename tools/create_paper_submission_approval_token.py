from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_submission_gate.token import create_token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tickets",
        default="release/order_ticket_generator/actual/order_ticket_snapshot.json",
    )
    parser.add_argument(
        "--output",
        default="release/paper_submission_gate/actual/paper_submission_token.json",
    )
    args = parser.parse_args()

    ticket_path = Path(args.tickets)
    digest = hashlib.sha256(ticket_path.read_bytes()).hexdigest()
    token = create_token(Path(args.output), digest)

    print("PAPER SUBMISSION TOKEN CREATED")
    print("Nonce:", token["nonce"])
    print("Expires:", token["expires_at"])
    print("Purpose:", token["purpose"])
    print("Ticket SHA256:", token["ticket_snapshot_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
