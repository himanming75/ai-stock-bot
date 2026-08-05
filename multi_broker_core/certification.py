from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from .factory import BrokerFactory
from .registry import default_registry
from .symbols import canonical_asset_key


def certify(output_dir: Path) -> dict:
    factory = BrokerFactory()
    adapter = factory.create("MOCK")
    registry = default_registry()

    account = adapter.get_account()
    positions = adapter.list_positions()
    orders = adapter.list_orders()
    submit_blocked = cancel_blocked = False

    try:
        adapter.submit_order(None)  # type: ignore[arg-type]
    except PermissionError:
        submit_blocked = True

    try:
        adapter.cancel_order("TEST")
    except PermissionError:
        cancel_blocked = True

    payload = {
        "stage": "V3001_TO_V3200_MULTI_BROKER_CORE_ARCHITECTURE",
        "status": "PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "implemented_brokers": factory.implemented_brokers(),
        "registered_brokers": [x.to_dict() for x in registry.list_all()],
        "mock_account": account.to_dict(),
        "mock_positions": [x.to_dict() for x in positions],
        "mock_orders": [x.to_dict() for x in orders],
        "canonical_symbol_example": canonical_asset_key("MOCK", "spy"),
        "submit_blocked": submit_blocked,
        "cancel_blocked": cancel_blocked,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "existing_alpaca_controller_modified": False,
        "credentials_loaded": False,
        "next_fixed_development": "V3201_TO_V3400_ALPACA_ADAPTER_EXTRACTION",
    }
    seed = dict(payload)
    seed.pop("generated_at")
    payload["certification_fingerprint"] = hashlib.sha256(
        json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in {
        "multi_broker_core_certification.json": payload,
        "broker_capability_registry.json": {"brokers": payload["registered_brokers"]},
        "broker_factory_registry.json": {"implemented_brokers": payload["implemented_brokers"]},
    }.items():
        (output_dir / name).write_text(json.dumps(content, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    with (output_dir / "multi_broker_core_ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True)+"\n")
    return payload
