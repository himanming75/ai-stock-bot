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

from alpaca_broker import (
    AlpacaPaperClient,
    AlpacaPaperConfig,
    AlpacaPaperOrderRecoveryManager,
    AtomicPaperOrderRecoveryStore,
    CredentialLoader,
    PaperOrderRecoveryRecord,
    UrllibHttpTransport,
)


RECOVERY_OPT_IN_ENV = "AI_STOCK_BOT_ENABLE_ALPACA_PAPER_ORDER_RECOVERY"
RECOVERY_CONFIRMATION_ENV = "AI_STOCK_BOT_ALPACA_PAPER_ORDER_RECOVERY_CONFIRMATION"
RECOVERY_CONFIRMATION_TEXT = "RECOVER ONE EXISTING ALPACA PAPER ORDER READ ONLY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--client-order-id", required=True)
    parser.add_argument("--symbol", required=True, choices=["AAPL", "SPY", "QQQ"])
    parser.add_argument("--side", required=True, choices=["buy", "sell"])
    parser.add_argument("--quantity", required=True, type=Decimal)
    parser.add_argument("--last-filled-quantity", required=True, type=Decimal)
    parser.add_argument("--last-status", required=True)
    parser.add_argument("--broker-order-id", default=None)
    args = parser.parse_args()

    environ = dict(os.environ)
    if environ.get(RECOVERY_OPT_IN_ENV, "").strip().upper() != "YES":
        raise SystemExit(f"{RECOVERY_OPT_IN_ENV}=YES is required")
    if environ.get(RECOVERY_CONFIRMATION_ENV, "").strip() != RECOVERY_CONFIRMATION_TEXT:
        raise SystemExit(
            f"{RECOVERY_CONFIRMATION_ENV} must equal: {RECOVERY_CONFIRMATION_TEXT}"
        )

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

    output = Path(args.repository_root).resolve() / "release" / "v114_00" / "actual_recovery"
    output.mkdir(parents=True, exist_ok=True)
    store = AtomicPaperOrderRecoveryStore(output / "paper_order_recovery.json")
    if store.load() is None:
        store.save(PaperOrderRecoveryRecord(
            schema_version=1,
            saved_at=datetime.now(timezone.utc),
            client_order_id=args.client_order_id,
            broker_order_id=args.broker_order_id,
            symbol=args.symbol,
            side=args.side,
            requested_quantity=args.quantity,
            last_filled_quantity=args.last_filled_quantity,
            last_status=args.last_status.lower(),
            submission_confirmed=True,
            terminal=False,
            recovery_generation=0,
        ))

    manager = AlpacaPaperOrderRecoveryManager(client=client, store=store)
    report = manager.recover()
    result = {
        "stage_range": "V113.01-V114.00",
        "status": "PASS",
        "validation_mode": "ACTUAL_ALPACA_PAPER_READ_ONLY_RECOVERY",
        **report.to_json_dict(),
        "paper_base_url": client.config.base_url,
        "write_network_enabled": client.config.network_write_enabled,
        "next_phase": "V114_01_ALPACA_PAPER_SESSION_SCHEDULER_FOUNDATION",
    }
    path = output / "actual_alpaca_paper_order_recovery_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
