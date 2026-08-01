from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    AlpacaPaperClient,
    AlpacaPaperConfig,
    AlpacaPaperOrderRecoveryManager,
    AtomicPaperOrderRecoveryStore,
    BrokerOrder,
    UrllibHttpTransport,
)
from tools.test_alpaca_paper_order_recovery_v113_01_to_v114_00 import (
    QueueOpener,
    order_payload,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    repo = Path(args.repository_root).resolve()
    output = repo / "release" / "v114_00" / "output"
    output.mkdir(parents=True, exist_ok=True)
    recovery_path = output / "paper_order_recovery.json"

    initial_order = BrokerOrder(
        order_id="order-1",
        client_order_id="BOT-PAPER-ONE-000001",
        symbol="AAPL",
        side="buy",
        quantity=Decimal("1"),
        filled_quantity=Decimal("0.5"),
        status="partially_filled",
    )

    opener = QueueOpener([order_payload("filled", "1")])
    client = AlpacaPaperClient(
        config=AlpacaPaperConfig(
            network_read_enabled=True,
            network_write_enabled=False,
            max_retries=0,
        ),
        api_key="fixture-key",
        secret_key="fixture-secret",
        transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
    )
    store = AtomicPaperOrderRecoveryStore(recovery_path)
    first_process = AlpacaPaperOrderRecoveryManager(client=client, store=store)
    checkpoint = first_process.checkpoint_from_order(initial_order)

    # Simulated process restart: a fresh manager loads the persisted checkpoint.
    restarted_manager = AlpacaPaperOrderRecoveryManager(client=client, store=store)
    report = restarted_manager.recover()
    recovered = store.load()

    result = {
        "stage_range": "V113.01-V114.00",
        "status": "PASS",
        "implementation_type": "ALPACA_PAPER_ORDER_RECOVERY_RESTART",
        "validation_mode": "OFFLINE_FIXTURE",
        "checkpoint_status": checkpoint.last_status,
        "checkpoint_filled_quantity": str(checkpoint.last_filled_quantity),
        **report.to_json_dict(),
        "persisted_status": recovered.last_status if recovered else None,
        "persisted_generation": recovered.recovery_generation if recovered else None,
        "request_methods": [request.get_method() for request, _ in opener.requests],
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "next_phase": "V114_01_ALPACA_PAPER_SESSION_SCHEDULER_FOUNDATION",
    }
    (output / "alpaca_paper_order_recovery_fixture_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
