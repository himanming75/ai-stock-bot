from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from order_ticket_generator.service import OrderTicketGeneratorService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execution",
        default="release/ai_execution_plan_bridge/actual/execution_plan_snapshot.json",
    )
    parser.add_argument(
        "--policy",
        default="release/order_ticket_generator/config/ticket_policy.json",
    )
    parser.add_argument(
        "--output",
        default="release/order_ticket_generator/actual/order_ticket_snapshot.json",
    )
    args = parser.parse_args()

    result = OrderTicketGeneratorService().run_file(
        Path(args.execution), Path(args.policy), Path(args.output)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
