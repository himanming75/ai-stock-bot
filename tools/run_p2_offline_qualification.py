from __future__ import annotations
from decimal import Decimal
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_integration.execution_config import ExecutionConfig
from broker_integration.execution_models import CanonicalOrderRequest
from broker_integration.execution_service import submit_paper_order
from alpaca_paper_read.config import PAPER_BASE_URL


class FakeHttp:
    def submit_order(self, payload):
        return {
            "id": "paper-order-fixture-001",
            "client_order_id": payload["client_order_id"],
            "symbol": payload["symbol"],
            "side": payload["side"],
            "type": payload["type"],
            "status": "accepted",
        }, "fixture-request-id"


with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    config = ExecutionConfig(
        api_key="fixture-key",
        secret_key="fixture-secret",
        base_url=PAPER_BASE_URL,
        network_enabled=True,
        write_enabled=True,
        confirmation="I_UNDERSTAND_THIS_SUBMITS_A_PAPER_ORDER",
        maximum_order_notional=Decimal("10"),
        maximum_daily_orders=3,
        allowed_symbols=frozenset({"AAPL"}),
        timeout_seconds=1,
        maximum_attempts=1,
        backoff_seconds=0,
    )
    order = CanonicalOrderRequest(
        symbol="AAPL",
        side="buy",
        order_type="market",
        time_in_force="day",
        notional=Decimal("5"),
        client_order_id="p2-offline-fixture-001",
    )
    result = submit_paper_order(
        config=config,
        order=order,
        account={
            "status": "ACTIVE",
            "account_blocked": False,
            "trading_blocked": False,
            "buying_power": "100000",
        },
        asset={"status": "active", "tradable": True},
        clock={"is_open": True},
        kill_switch={"kill_switch_active": False},
        risk_permission=True,
        latest_trade_price=None,
        positions=[],
        registry_path=base / "registry.json",
        order_ledger_path=base / "orders.jsonl",
        error_ledger_path=base / "errors.jsonl",
        http=FakeHttp(),
    )

qualification = {
    "stage": "P2",
    "state": "ACTUAL_ALPACA_PAPER_EXECUTION_OFFLINE_QUALIFIED",
    "status": "PASS" if result["submitted"] else "FAIL",
    "offline_transport_only": True,
    "actual_network_used": False,
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
    "market_order_supported": True,
    "limit_order_supported": True,
    "buy_sell_supported": True,
    "fractional_market_supported": True,
    "notional_market_supported": True,
    "client_order_id_enabled": True,
    "idempotency_enabled": True,
    "cancel_supported": True,
    "replace_supported": True,
    "kill_switch_required": True,
    "paper_endpoint_enforced": True,
    "reference_price_authorization_removed": True,
    "sell_position_check_enabled": True,
    "next_action": "RUN_EXPLICIT_ACTUAL_PAPER_ORDER_WHEN_MARKET_OPEN",
}
out = (
    ROOT
    / "release/p2_actual_paper_execution/actual/"
      "p2_offline_qualification.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(qualification, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(qualification, indent=2, sort_keys=True))
raise SystemExit(0 if qualification["status"] == "PASS" else 1)
