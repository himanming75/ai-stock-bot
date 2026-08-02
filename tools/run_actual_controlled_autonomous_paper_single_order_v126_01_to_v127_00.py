from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import argparse
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    AlpacaPaperClient,
    AlpacaPaperConfig,
    CredentialLoader,
    UrllibHttpTransport,
)
from autonomous_paper_runtime.controlled_single_order import (
    ControlledAutonomousPaperSingleOrder,
    ControlledSingleOrderRequest,
)


ENABLE_ENV = "AI_STOCK_BOT_ENABLE_ACTUAL_CONTROLLED_PAPER_ORDER"
CONFIRM_ENV = "AI_STOCK_BOT_ACTUAL_CONTROLLED_PAPER_ORDER_CONFIRMATION"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--estimated-price", required=True)
    args = parser.parse_args()

    root = Path(args.repository_root).resolve()
    readiness_path = (
        root / "release/v126_00/readiness/paper_write_readiness_result.json"
    )
    if not readiness_path.exists():
        raise SystemExit(f"missing readiness certificate: {readiness_path}")
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))

    environ = dict(os.environ)
    enabled = environ.get(ENABLE_ENV, "").strip().upper() == "YES"
    confirmation = environ.get(CONFIRM_ENV, "").strip()

    key, secret = CredentialLoader().load(environ)
    broker = AlpacaPaperClient(
        config=AlpacaPaperConfig(
            network_read_enabled=True,
            network_write_enabled=True,
            max_retries=0,
        ),
        api_key=key,
        secret_key=secret,
        transport=UrllibHttpTransport(),
    )

    runner = ControlledAutonomousPaperSingleOrder()
    result = runner.execute(
        broker=broker,
        request=ControlledSingleOrderRequest(
            symbol=args.symbol,
            side="buy",
            quantity=Decimal("1"),
            estimated_price=Decimal(args.estimated_price),
        ),
        readiness_result=readiness,
        submit_enabled=enabled,
        approval_text=confirmation,
        client_order_nonce=str(time.time_ns()),
    )

    output = root / "release/v127_00/actual"
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage_range": "V126.01-V127.00",
        "status": "PASS",
        "implementation_type": "CONTROLLED_AUTONOMOUS_PAPER_SINGLE_ORDER",
        "validation_mode": "ACTUAL_ALPACA_PAPER_CONTROLLED",
        **result.to_json_dict(),
        "next_phase": (
            "V127_01_PAPER_ORDER_LIFECYCLE_TRACKING"
            if result.decision.value == "SUBMITTED"
            else "V127_01_EXISTING_PAPER_ORDER_LIFECYCLE_TRACKING"
        ),
    }
    path = output / "actual_controlled_paper_single_order_result.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
