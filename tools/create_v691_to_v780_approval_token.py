from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from approval_submission_safety.io import read_json, write_json
from approval_submission_safety.token import create_token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ticket-bundle",
        default=(
            "release/v641_690_paper_order_ticket_builder/"
            "actual/paper_order_ticket_bundle.json"
        ),
    )
    parser.add_argument(
        "--ticket-index",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--output",
        default=(
            "release/v691_780_approval_submission_safety/"
            "actual/approval_token.json"
        ),
    )
    parser.add_argument("--ttl-seconds", type=int, default=300)
    args = parser.parse_args()

    secret = os.environ.get("AI_STOCK_BOT_SUBMISSION_SECRET", "")
    if not secret:
        raise RuntimeError("AI_STOCK_BOT_SUBMISSION_SECRET_MISSING")

    bundle = read_json(Path(args.ticket_bundle))
    tickets = bundle.get("valid_tickets", [])
    if not tickets:
        raise RuntimeError("NO_VALID_TICKETS_AVAILABLE")
    if args.ticket_index < 0 or args.ticket_index >= len(tickets):
        raise RuntimeError("TICKET_INDEX_OUT_OF_RANGE")

    ticket = tickets[args.ticket_index]
    scope = {
        "environment": "paper",
        "operation": "paper_order_submission_review",
        "ticket_id": ticket.get("ticket_id"),
        "idempotency_key": ticket.get("idempotency_key"),
        "request_fingerprint": ticket.get("idempotency_key"),
    }
    token = create_token(
        scope=scope,
        secret=secret,
        ttl_seconds=args.ttl_seconds,
    )
    write_json(Path(args.output), token)
    print(
        json.dumps(
            {
                "status": "TOKEN_CREATED",
                "ticket_id": ticket.get("ticket_id"),
                "expires_at": token["body"]["expires_at"],
                "nonce": token["body"]["nonce"],
                "raw_secret_printed": False,
                "output": args.output,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
