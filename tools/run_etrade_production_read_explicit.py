from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_broker_core.factory import BrokerFactory
from multi_broker_etrade.credentials import (
    EnvironmentETradeCredentialProvider,
)
from multi_broker_etrade.factory_registration import (
    register_etrade_adapter,
)
from multi_broker_etrade.transport import (
    UrllibETradeOAuthTransport,
)
from multi_broker_etrade_routing.policy import (
    ProductionReadOnlyPolicy,
)


def main() -> int:
    policy = ProductionReadOnlyPolicy.from_environment()
    policy.assert_production_read_allowed()

    credentials = (
        EnvironmentETradeCredentialProvider().load()
    )
    if credentials.environment.upper() != "PRODUCTION":
        raise RuntimeError(
            "ETRADE_ENVIRONMENT must be PRODUCTION"
        )

    requested = os.environ.get(
        "ETRADE_DEFAULT_ACCOUNT_ID_KEY",
        "",
    ).strip()
    if requested:
        policy.assert_account_allowed(requested)

    factory = register_etrade_adapter(
        BrokerFactory()
    )
    adapter = factory.create(
        "ETRADE",
        transport=UrllibETradeOAuthTransport(
            credentials
        ),
        account_id_key=requested or None,
    )

    account = adapter.get_account()
    positions = adapter.list_positions()
    orders = adapter.list_orders()

    result = {
        "stage": (
            "ETRADE_PRODUCTION_READ_ONLY_EXPLICIT"
        ),
        "status": "PASS",
        "generated_at": (
            datetime.now(timezone.utc).isoformat()
        ),
        "account": account.to_dict(),
        "positions": [
            item.to_dict()
            for item in positions
        ],
        "orders": [
            item.to_dict()
            for item in orders
        ],
        "actual_external_network_used": True,
        "actual_broker_read_performed": True,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }

    path = Path(
        "release/v4001_4200_etrade_production_routing/"
        "actual/explicit_production_read_result.json"
    )
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
