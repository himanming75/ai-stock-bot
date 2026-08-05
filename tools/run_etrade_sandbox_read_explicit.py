from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_broker_etrade_oauth.sandbox_read import build_sandbox_adapter


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-id-key", default="")
    parser.add_argument(
        "--output",
        default=(
            "release/v3601_3800_etrade_oauth_session/"
            "actual/explicit_sandbox_read_result.json"
        ),
    )
    args = parser.parse_args()

    adapter = build_sandbox_adapter(
        consumer_key=required("ETRADE_CONSUMER_KEY"),
        consumer_secret=required("ETRADE_CONSUMER_SECRET"),
        access_token=required("ETRADE_ACCESS_TOKEN"),
        access_secret=required("ETRADE_ACCESS_SECRET"),
        account_id_key=args.account_id_key or None,
    )

    account = adapter.get_account()
    positions = adapter.list_positions()
    orders = adapter.list_orders()

    result = {
        "status": "PASS",
        "environment": "SANDBOX",
        "account": account.to_dict(),
        "positions": [item.to_dict() for item in positions],
        "orders": [item.to_dict() for item in orders],
        "actual_external_network_used": True,
        "actual_broker_read_performed": True,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
