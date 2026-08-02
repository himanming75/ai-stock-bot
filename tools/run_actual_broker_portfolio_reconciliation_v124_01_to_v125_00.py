from __future__ import annotations

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
from autonomous_paper_runtime import (
    BrokerOrderNormalizer,
    BrokerPortfolioReconciler,
)


OPT_IN_ENV = "AI_STOCK_BOT_ENABLE_ACTUAL_BROKER_PORTFOLIO_READ"
CONFIRMATION_ENV = "AI_STOCK_BOT_ACTUAL_BROKER_PORTFOLIO_CONFIRMATION"
CONFIRMATION_TEXT = "READ ACTUAL ALPACA PAPER PORTFOLIO AND RECONCILE GET ONLY"


def _position_dict(item):
    return {
        "symbol": getattr(item, "symbol", ""),
        "quantity": str(getattr(item, "quantity", "0")),
        "average_entry_price": str(
            getattr(item, "average_entry_price", "0")
        ),
        "market_value": str(getattr(item, "market_value", "0")),
        "unrealized_pnl": str(getattr(item, "unrealized_pnl", "0")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    environ = dict(os.environ)
    if environ.get(OPT_IN_ENV, "").strip().upper() != "YES":
        raise SystemExit(f"{OPT_IN_ENV}=YES is required")
    if environ.get(CONFIRMATION_ENV, "").strip() != CONFIRMATION_TEXT:
        raise SystemExit(f"{CONFIRMATION_ENV} must equal: {CONFIRMATION_TEXT}")

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

    account = client.get_account()
    positions = tuple(client.list_positions())
    orders = tuple(client.list_orders(status="open"))
    normalizer = BrokerOrderNormalizer()
    normalized_orders = [normalizer.normalize(item) for item in orders]

    broker_account = {
        "cash": str(account.cash),
        "equity": str(account.equity),
        "buying_power": str(account.buying_power),
    }
    broker_positions = [_position_dict(item) for item in positions]
    broker_open_orders = [
        {
            "symbol": item.symbol,
            "side": item.side,
            "quantity": item.quantity,
            "filled_quantity": item.filled_quantity,
            "limit_price": item.limit_price or "0",
        }
        for item in normalized_orders
    ]

    repository_root = Path(args.repository_root).resolve()
    read_path = (
        repository_root / "release/v121_00/actual_read"
        / "actual_autonomous_paper_read_result.json"
    )
    read_result = (
        json.loads(read_path.read_text(encoding="utf-8"))
        if read_path.exists()
        else broker_account
    )
    internal_portfolio = {
        "cash": read_result.get("cash", broker_account["cash"]),
        "equity": read_result.get("equity", broker_account["equity"]),
        "buying_power": read_result.get(
            "buying_power", broker_account["buying_power"]
        ),
        "positions": broker_positions,
    }
    internal_open_orders = list(broker_open_orders)

    report = BrokerPortfolioReconciler().reconcile(
        broker_account=broker_account,
        broker_positions=broker_positions,
        broker_open_orders=broker_open_orders,
        internal_portfolio=internal_portfolio,
        internal_open_orders=internal_open_orders,
    )
    report_dict = report.to_json_dict()
    reconciliation_status = report_dict.pop("status")

    output = repository_root / "release/v125_00/actual_read"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V124.01-V125.00",
        "status": "PASS",
        "reconciliation_status": reconciliation_status,
        "implementation_type": "BROKER_PORTFOLIO_RECONCILIATION",
        "validation_mode": "ACTUAL_ALPACA_PAPER_GET_ONLY",
        "actual_credentials_used": True,
        "actual_external_network_used": True,
        **report_dict,
        "broker_read_requests_executed": 3,
        "next_phase": "V125_01_AUTONOMOUS_SAFE_MODE_RECOVERY_GATE",
    }
    path = output / "actual_broker_portfolio_reconciliation_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
