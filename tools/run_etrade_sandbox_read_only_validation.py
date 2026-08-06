from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etrade_sandbox.client import (
    ETradeSandboxReadOnlyClient,
)
from etrade_sandbox.core import (
    ETradeCredentialVault,
)
from etrade_sandbox.parsing import (
    extract_accounts,
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "--symbols",
    default="AAPL,MSFT",
)
args = parser.parse_args()

vault = ETradeCredentialVault(
    Path(
        "runtime/secrets/"
        "etrade_sandbox.dpapi.json"
    )
)
if not vault.exists():
    raise SystemExit(
        "Vault missing. Run OAuth wizard first."
    )
credentials = vault.load()
client = ETradeSandboxReadOnlyClient(
    consumer_key=credentials["consumer_key"],
    consumer_secret=credentials[
        "consumer_secret"
    ],
    access_token=credentials["access_token"],
    access_token_secret=credentials[
        "access_token_secret"
    ],
)

account_response = client.list_accounts()
accounts = extract_accounts(
    account_response
)
balances = {}
portfolios = {}
orders = {}
errors = []

for account in accounts:
    key = account.get("account_id_key")
    if not key:
        continue
    for name, target, call in (
        ("balance", balances, lambda: client.balance(key)),
        ("portfolio", portfolios, lambda: client.portfolio(key)),
        ("orders", orders, lambda: client.orders(key)),
    ):
        try:
            target[key] = call()
        except Exception as exc:
            errors.append({
                "account_id_key": key,
                "operation": name,
                "error": str(exc),
            })

quote = None
try:
    quote = client.quote(
        args.symbols.split(",")
    )
except Exception as exc:
    errors.append({
        "operation": "quote",
        "error": str(exc),
    })

result = {
    "stage": "ETRADE_SANDBOX_ACTUAL_READ_ONLY_VALIDATION",
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "status": "PASS" if accounts else "BLOCKED",
    "environment": "SANDBOX",
    "read_only": True,
    "write_enabled": False,
    "accounts": accounts,
    "balances": balances,
    "portfolios": portfolios,
    "orders": orders,
    "quote": quote,
    "errors": errors,
    "actual_external_network_used": True,
    "actual_broker_read_performed": True,
    "actual_broker_write_performed": False,
    "actual_order_submission_performed": False,
    "actual_order_cancel_performed": False,
}
out = Path(
    "release/etrade_sandbox_live_read/actual"
)
out.mkdir(parents=True, exist_ok=True)
(out / "etrade_sandbox_read_only_validation.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(
    0 if result["status"] == "PASS" else 2
)
