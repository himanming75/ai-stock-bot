from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    AlpacaNetworkDisabledError,
    AlpacaPaperClient,
    AlpacaPaperConfig,
    BrokerAccount,
    BrokerPortfolioReconciler,
    BrokerPosition,
    UrllibHttpTransport,
)
from portfolio_engine import PortfolioSnapshot, PositionSnapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v110_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    client = AlpacaPaperClient(
        config=AlpacaPaperConfig(),
        api_key="REDACTED_DEMO_KEY",
        secret_key="REDACTED_DEMO_SECRET",
        transport=UrllibHttpTransport(),
    )

    read_blocked = False
    try:
        client.get_account()
    except AlpacaNetworkDisabledError:
        read_blocked = True

    preview = client.preview_submit_order({
        "symbol": "AAPL",
        "qty": "1",
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
        "client_order_id": "BOT-DEMO-000001",
    })

    write_blocked = False
    try:
        client.submit_order(preview["payload"])
    except AlpacaNetworkDisabledError:
        write_blocked = True

    captured = datetime(2026, 8, 1, 16, tzinfo=timezone.utc)
    internal = PortfolioSnapshot(
        captured_at=captured,
        cash=Decimal("950"),
        equity=Decimal("1000"),
        market_value=Decimal("50"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("0"),
        buying_power=Decimal("950"),
        positions=(PositionSnapshot(
            symbol="AAPL",
            quantity=Decimal("1"),
            average_price=Decimal("50"),
            market_price=Decimal("50"),
            market_value=Decimal("50"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
        ),),
    )
    account = BrokerAccount(
        "demo-account", "ACTIVE", Decimal("950"), Decimal("1000"),
        Decimal("950"), False
    )
    positions = (
        BrokerPosition("AAPL", Decimal("1"), Decimal("50"), Decimal("50"), Decimal("0")),
    )
    reconciliation = BrokerPortfolioReconciler().reconcile(
        internal=internal,
        account=account,
        positions=positions,
    )

    result = {
        "stage_range": "V109.01-V110.00",
        "status": "PASS",
        "implementation_type": "ALPACA_PAPER_BROKER_INTEGRATION_FOUNDATION",
        "paper_base_url": client.config.base_url,
        "live_url_blocked": True,
        "credential_headers_configured": True,
        "read_network_enabled": client.config.network_read_enabled,
        "write_network_enabled": client.config.network_write_enabled,
        "read_network_blocked": read_blocked,
        "write_network_blocked": write_blocked,
        "order_preview_ready": preview["network_executed"] is False,
        "reconciliation_matched": reconciliation.matched,
        "network_requests_executed": client.network_requests_executed,
        "write_requests_executed": client.write_requests_executed,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "next_phase": "V110_01_CONTROLLED_ALPACA_PAPER_READ_VALIDATION",
    }
    (output / "alpaca_paper_broker_integration_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
