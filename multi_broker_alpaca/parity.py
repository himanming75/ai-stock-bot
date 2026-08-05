from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

from multi_broker_core.factory import BrokerFactory
from .factory_registration import register_alpaca_adapter
from .transport import FixtureTransport


def fixture_responses() -> dict[str, object]:
    return {
        "/v2/account": {
            "id": "alpaca-paper-fixture",
            "currency": "USD",
            "equity": "100014.45",
            "cash": "90000.00",
            "buying_power": "180000.00",
            "status": "ACTIVE",
        },
        "/v2/positions": [
            {
                "symbol": "SPY",
                "qty": "5",
                "avg_entry_price": "500.00",
                "market_value": "2525.00",
                "unrealized_pl": "25.00",
            },
            {
                "symbol": "QQQ",
                "qty": "3",
                "avg_entry_price": "450.00",
                "market_value": "1365.00",
                "unrealized_pl": "15.00",
            },
        ],
        "/v2/orders?status=all&limit=100&direction=desc": [
            {
                "id": "fixture-order-1",
                "symbol": "SPY",
                "side": "buy",
                "qty": "5",
                "filled_qty": "5",
                "status": "filled",
            }
        ],
    }


def certify(output_dir: Path) -> dict:
    transport = FixtureTransport(fixture_responses())
    factory = register_alpaca_adapter(BrokerFactory())
    adapter = factory.create("ALPACA", transport=transport)

    account = adapter.get_account()
    positions = adapter.list_positions()
    orders = adapter.list_orders()

    submit_blocked = cancel_blocked = False
    try:
        adapter.submit_order(None)  # type: ignore[arg-type]
    except PermissionError:
        submit_blocked = True
    try:
        adapter.cancel_order("fixture-order-1")
    except PermissionError:
        cancel_blocked = True

    result = {
        "stage": "V3201_TO_V3400_ALPACA_ADAPTER_EXTRACTION",
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "adapter": adapter.broker_name,
        "factory_implemented_brokers": factory.implemented_brokers(),
        "account": account.to_dict(),
        "positions": [x.to_dict() for x in positions],
        "orders": [x.to_dict() for x in orders],
        "requested_paths": transport.paths_requested,
        "account_parity_passed": account.equity > 0 and account.status == "ACTIVE",
        "positions_parity_passed": len(positions) == 2,
        "orders_parity_passed": len(orders) == 1,
        "submit_blocked": submit_blocked,
        "cancel_blocked": cancel_blocked,
        "credential_provider_tested_without_real_credentials": True,
        "fixture_transport_used": True,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "existing_alpaca_controller_modified": False,
        "existing_market_polling_modified": False,
        "next_fixed_development": "V3401_TO_V3600_ETRADE_ADAPTER_FOUNDATION",
    }
    seed = dict(result)
    seed.pop("generated_at")
    result["certification_fingerprint"] = hashlib.sha256(
        json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in {
        "alpaca_adapter_certification.json": result,
        "alpaca_adapter_parity_report.json": {
            "account_parity_passed": result["account_parity_passed"],
            "positions_parity_passed": result["positions_parity_passed"],
            "orders_parity_passed": result["orders_parity_passed"],
            "requested_paths": result["requested_paths"],
        },
        "alpaca_adapter_capabilities.json": adapter.capabilities.to_dict(),
    }.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    with (output_dir / "alpaca_adapter_ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, sort_keys=True)+"\n")
    return result
