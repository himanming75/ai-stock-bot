from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from p3_micro_paper.service import P3MicroPaperOrderService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument(
        "--ticket",
        default="release/p3_micro_paper/actual/p3_micro_ticket.json",
    )
    parser.add_argument(
        "--token",
        default="release/p3_micro_paper/actual/p3_micro_token.json",
    )
    parser.add_argument(
        "--output",
        default="release/p3_micro_paper/actual/p3_micro_result.json",
    )
    args = parser.parse_args()

    result = P3MicroPaperOrderService().validate_and_submit(
        ticket_path=Path(args.ticket),
        token_path=Path(args.token),
        nonce=args.nonce,
        output_path=Path(args.output),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
