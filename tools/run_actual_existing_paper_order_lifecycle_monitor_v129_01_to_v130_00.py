from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    AlpacaPaperClient,
    AlpacaPaperConfig,
    CredentialLoader,
    UrllibHttpTransport,
)
from autonomous_paper_runtime.lifecycle_monitor import (
    ExistingPaperOrderLifecycleMonitor,
    LifecycleLedger,
    build_snapshot,
)


ENABLE_ENV = "AI_STOCK_BOT_ENABLE_ACTUAL_LIFECYCLE_MONITOR"
CONFIRM_ENV = "AI_STOCK_BOT_ACTUAL_LIFECYCLE_MONITOR_CONFIRMATION"
CONFIRMATION_TEXT = "MONITOR ACTUAL ALPACA PAPER ORDER GET ONLY"


def _value(item, *names, default=""):
    for name in names:
        value = getattr(item, name, None)
        if value not in (None, ""):
            if hasattr(value, "value"):
                value = value.value
            return value
    for raw_name in ("raw", "_raw", "data", "_data"):
        raw = getattr(item, raw_name, None)
        if isinstance(raw, dict):
            for name in names:
                value = raw.get(name)
                if value not in (None, ""):
                    return value
    return default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--client-order-id",
        default="single-60d3c5406e5226ae71d7",
    )
    parser.add_argument("--max-polls", type=int, default=3)
    parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    parser.add_argument(
        "--stop-on-material-transition",
        action="store_true",
    )
    args = parser.parse_args()

    environ = dict(os.environ)
    if environ.get(ENABLE_ENV, "").strip().upper() != "YES":
        raise SystemExit(f"{ENABLE_ENV}=YES is required")
    if environ.get(CONFIRM_ENV, "").strip() != CONFIRMATION_TEXT:
        raise SystemExit(f"{CONFIRM_ENV} must equal: {CONFIRMATION_TEXT}")

    key, secret = CredentialLoader().load(environ)
    client = AlpacaPaperClient(
        config=AlpacaPaperConfig(
            network_read_enabled=True,
            network_write_enabled=False,
            max_retries=2,
        ),
        api_key=key,
        secret_key=secret,
        transport=UrllibHttpTransport(),
    )

    root = Path(args.repository_root).resolve()
    ledger_path = (
        root / "release/v130_00/actual"
        / "actual_existing_order_lifecycle_ledger.jsonl"
    )
    monitor = ExistingPaperOrderLifecycleMonitor(
        ledger=LifecycleLedger(ledger_path)
    )

    def poll(sequence: int):
        broker_order = client.get_order_by_client_id(
            args.client_order_id
        )
        broker_positions = tuple(client.list_positions())
        broker_account = client.get_account()

        order = {
            "id": _value(broker_order, "order_id", "id"),
            "client_order_id": _value(
                broker_order, "client_order_id"
            ),
            "symbol": _value(broker_order, "symbol"),
            "side": _value(broker_order, "side"),
            "status": _value(broker_order, "status"),
            "quantity": _value(
                broker_order, "quantity", "qty", default="0"
            ),
            "filled_quantity": _value(
                broker_order,
                "filled_quantity",
                "filled_qty",
                default="0",
            ),
            "average_fill_price": _value(
                broker_order,
                "average_fill_price",
                "filled_avg_price",
                default="0",
            ),
        }
        positions = [
            {
                "symbol": _value(item, "symbol"),
                "quantity": _value(
                    item, "quantity", "qty", default="0"
                ),
                "average_entry_price": _value(
                    item,
                    "average_entry_price",
                    "average_price",
                    default="0",
                ),
            }
            for item in broker_positions
        ]
        account = {
            "cash": _value(broker_account, "cash", default="0"),
            "equity": _value(
                broker_account, "equity", default="0"
            ),
        }

        return build_snapshot(
            sequence=sequence,
            observed_at=datetime.now(timezone.utc).isoformat(),
            order=order,
            positions=positions,
            account=account,
        )

    report = monitor.monitor(
        poller=poll,
        max_polls=args.max_polls,
        poll_interval_seconds=args.poll_interval_seconds,
        stop_on_material_transition=args.stop_on_material_transition,
        network_requests_per_poll=3,
    )

    output = root / "release/v130_00/actual"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V129.01-V130.00",
        "status": "PASS",
        "implementation_type": "EXISTING_PAPER_ORDER_LIFECYCLE_MONITORING_RUNTIME",
        "validation_mode": "ACTUAL_ALPACA_PAPER_GET_ONLY",
        "actual_credentials_used": True,
        "actual_external_network_used": True,
        **report.to_json_dict(),
        "next_phase": (
            "V130_01_FILL_LEDGER_AND_PORTFOLIO_COMMIT"
            if report.decision.value == "FILLED_COMPLETE"
            else "V130_01_ORDER_COMPLETION_AND_NEXT_ORDER_UNLOCK_GATE"
            if report.terminal
            else "V130_01_CONTINUE_EXISTING_ORDER_MONITOR"
        ),
    }
    path = output / "actual_existing_paper_order_lifecycle_monitor_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    print(f"LEDGER_FILE={ledger_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
