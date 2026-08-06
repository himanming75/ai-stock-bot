from __future__ import annotations
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etrade_sandbox.core import (
    ETradeCredentialVault,
)
from etrade_sandbox.oauth_flow import (
    ETradeOAuthFlow,
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "action",
    choices=["renew", "revoke"],
)
args = parser.parse_args()

vault = ETradeCredentialVault(
    Path(
        "runtime/secrets/"
        "etrade_sandbox.dpapi.json"
    )
)
data = vault.load()
flow = ETradeOAuthFlow(
    consumer_key=data["consumer_key"],
    consumer_secret=data["consumer_secret"],
)
if args.action == "renew":
    print(flow.renew(
        access_token=data["access_token"],
        access_token_secret=data[
            "access_token_secret"
        ],
    ))
    data["last_renewed_at"] = (
        datetime.now(timezone.utc).isoformat()
    )
    vault.save(data)
    print("TOKEN RENEWED")
else:
    if input(
        "Type REVOKE to continue: "
    ) != "REVOKE":
        raise SystemExit("Cancelled.")
    print(flow.revoke(
        access_token=data["access_token"],
        access_token_secret=data[
            "access_token_secret"
        ],
    ))
    data["revoked"] = True
    data["revoked_at"] = (
        datetime.now(timezone.utc).isoformat()
    )
    vault.save(data)
    print("TOKEN REVOKED")
