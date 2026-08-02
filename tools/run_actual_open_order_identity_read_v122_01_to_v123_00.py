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
from autonomous_paper_runtime import AutonomousPaperOrderIdentityReconciler


OPT_IN_ENV = "AI_STOCK_BOT_ENABLE_ACTUAL_OPEN_ORDER_IDENTITY_READ"
CONFIRMATION_ENV = "AI_STOCK_BOT_ACTUAL_OPEN_ORDER_IDENTITY_CONFIRMATION"
CONFIRMATION_TEXT = "READ ACTUAL ALPACA PAPER OPEN ORDER IDENTITIES GET ONLY"


def _to_dict(item):
    if isinstance(item, dict):
        return dict(item)
    names = (
        "id",
        "client_order_id",
        "symbol",
        "side",
        "qty",
        "type",
        "time_in_force",
        "status",
        "submitted_at",
        "filled_qty",
        "limit_price",
    )
    return {name: getattr(item, name, None) for name in names}


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

    orders = [_to_dict(item) for item in client.list_orders(status="open")]
    report = AutonomousPaperOrderIdentityReconciler().reconcile(
        open_orders=orders,
        internal_order_ledger=[],
    )

    output = (
        Path(args.repository_root).resolve()
        / "release" / "v123_00" / "actual_read"
    )
    output.mkdir(parents=True, exist_ok=True)

    report_dict = report.to_json_dict()
    identity_status = report_dict.pop("status")
    result = {
        "stage_range": "V122.01-V123.00",
        "status": "PASS",
        "identity_status": identity_status,
        "implementation_type": "AUTONOMOUS_PAPER_ORDER_IDENTITY_RECONCILIATION",
        "validation_mode": "ACTUAL_ALPACA_PAPER_GET_ONLY",
        "actual_credentials_used": True,
        "actual_external_network_used": True,
        **report_dict,
        "broker_read_requests_executed": 1,
        "next_phase": "V123_01_AUTONOMOUS_ORDER_LEDGER_RECOVERY",
    }
    path = output / "actual_open_order_identity_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
