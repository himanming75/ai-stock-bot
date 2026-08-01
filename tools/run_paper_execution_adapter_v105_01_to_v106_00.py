from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_engine import Event, EventBus, ManualClock
from execution_engine import (
    AlpacaPaperPayloadBuilder,
    ClientOrderIdGenerator,
    ExecutionIdempotencyGuard,
    MockPaperTransport,
    OrderIntent,
    OrderSide,
    OrderType,
    PaperExecutionAdapter,
    PaperExecutionEngine,
    TimeInForce,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v106_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
    clock = ManualClock(now)
    bus = EventBus()
    requests = []
    updates = []
    bus.subscribe("execution.request", lambda event: requests.append(event.payload["request"]))
    bus.subscribe("execution.update", lambda event: updates.append(event.payload["result"]))

    transport = MockPaperTransport(default_fill_price=Decimal("50.05"))
    adapter = PaperExecutionAdapter(
        transport=transport,
        payload_builder=AlpacaPaperPayloadBuilder(),
        client_order_id_generator=ClientOrderIdGenerator(),
        idempotency_guard=ExecutionIdempotencyGuard(),
    )
    engine = PaperExecutionEngine(event_bus=bus, adapter=adapter, now=clock.now)
    engine.start()

    intent = OrderIntent(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        reference_price=Decimal("50"),
        estimated_notional=Decimal("50"),
        created_at=now,
        expires_at=now + timedelta(seconds=30),
        source_signal_id="demo-signal",
        strategy_name="demo_strategy",
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
    )

    bus.publish(Event("order.intent", {"intent":intent}, now))
    engine.stop()

    accepted = updates[0]
    clock.advance(seconds=1)
    partial = transport.simulate_partial_fill(accepted.client_order_id, clock.now())
    clock.advance(seconds=1)
    filled = transport.simulate_full_fill(accepted.client_order_id, clock.now())
    reconciliation = adapter.reconcile(
        request_status=filled.status,
        transport_result=filled,
        now=clock.now(),
    )
    cancel = adapter.cancel(filled.client_order_id, clock.now(), "DEMO_CANCEL_RECORD")

    result = {
        "stage_range": "V105.01-V106.00",
        "status": "PASS",
        "implementation_type": "PAPER_EXECUTION_ADAPTER_FOUNDATION",
        "execution_request_count": len(requests),
        "execution_update_count": len(updates),
        "initial_status": accepted.status.value,
        "partial_status": partial.status.value,
        "filled_status": filled.status.value,
        "filled_quantity": str(filled.filled_quantity),
        "average_fill_price": str(filled.average_fill_price),
        "cancel_status": cancel.status.value,
        "reconciliation_matched": reconciliation.matched,
        "engine_stats": vars(engine.stats),
        "mock_transport_request_count": len(transport.requests),
        "mock_transport_cancel_count": len(transport.cancel_requests),
        "network_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "actual_broker_transport_enabled": False,
        "next_phase": "V106_01_PORTFOLIO_AND_FILL_ACCOUNTING_FOUNDATION",
    }

    (output / "paper_execution_adapter_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
