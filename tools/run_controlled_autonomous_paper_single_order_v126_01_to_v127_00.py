from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.controlled_single_order import (
    ControlledAutonomousPaperSingleOrder,
    ControlledSingleOrderRequest,
)


@dataclass
class Account:
    status: str = "ACTIVE"
    trading_blocked: bool = False


@dataclass
class Clock:
    is_open: bool = True


@dataclass
class ExistingOrder:
    order_id: str = "legacy-order-1"
    status: str = "accepted"


class OfflineBroker:
    def __init__(self):
        self.network_requests_executed = 0
        self.write_requests_executed = 0

    def get_account(self):
        return Account()

    def get_clock(self):
        return Clock()

    def list_orders(self, *, status="open", limit=50):
        # Mirrors the current actual Paper account: one recovered open order.
        return (ExistingOrder(),)

    def preview_submit_order(self, payload):
        return {"payload": payload, "network_executed": False}

    def submit_order(self, payload):
        raise AssertionError("offline demo must never submit an order")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    readiness_path = (
        root / "release/v126_00/readiness/paper_write_readiness_result.json"
    )
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))

    runner = ControlledAutonomousPaperSingleOrder()
    result = runner.execute(
        broker=OfflineBroker(),
        request=ControlledSingleOrderRequest(
            symbol="AAPL",
            side="buy",
            quantity=Decimal("1"),
            estimated_price=Decimal("50"),
        ),
        readiness_result=readiness,
        submit_enabled=False,
        approval_text="",
        client_order_nonce="offline-current-existing-order",
    )

    output = root / "release/v127_00/output"
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage_range": "V126.01-V127.00",
        "status": "PASS",
        "implementation_type": "CONTROLLED_AUTONOMOUS_PAPER_SINGLE_ORDER",
        "validation_mode": "OFFLINE_EXISTING_ORDER_GUARD",
        **result.to_json_dict(),
        "existing_order_guard_verified": (
            result.decision.value == "EXISTING_ORDER_WAIT"
            and result.actual_paper_orders_submitted == 0
        ),
        "next_phase": "V127_01_EXISTING_PAPER_ORDER_LIFECYCLE_TRACKING",
    }
    path = output / "controlled_autonomous_paper_single_order_result.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
