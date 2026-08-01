from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import ControlledPaperOrderOptIn, UrllibHttpTransport


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--symbol", required=True, choices=["AAPL", "SPY", "QQQ"])
    parser.add_argument("--side", required=True, choices=["buy", "sell"])
    parser.add_argument("--quantity", required=True, type=Decimal)
    parser.add_argument("--reference-price", required=True, type=Decimal)
    args = parser.parse_args()

    client_order_id = "BOT-PAPER-ONE-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    optin = ControlledPaperOrderOptIn.from_environment(
        dict(os.environ),
        transport=UrllibHttpTransport(),
        timeout_seconds=10.0,
        max_retries=0,
    )
    plan = optin.build_plan(
        symbol=args.symbol,
        side=args.side,
        quantity=args.quantity,
        reference_price=args.reference_price,
        client_order_id=client_order_id,
    )
    report = optin.submit_once(plan)

    output = Path(args.repository_root).resolve() / "release" / "v112_00" / "actual_order"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V111.01-V112.00",
        "status": "PASS",
        "validation_mode": "ACTUAL_ALPACA_PAPER_SINGLE_ORDER",
        **report.to_json_dict(),
        "paper_base_url": optin.client.config.base_url,
        "write_network_enabled": optin.client.config.network_write_enabled,
        "next_phase": "V112_01_ACTUAL_ALPACA_PAPER_ORDER_VALIDATION",
    }
    path = output / "actual_alpaca_paper_single_order_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
