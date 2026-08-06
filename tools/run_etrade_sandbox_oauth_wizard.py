from __future__ import annotations
import getpass
import json
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etrade_sandbox.core import (
    ETradeCredentialVault,
    mask,
)
from etrade_sandbox.oauth_flow import (
    ETradeOAuthFlow,
)

VAULT = Path(
    "runtime/secrets/etrade_sandbox.dpapi.json"
)

print("=== E*TRADE SANDBOX OAUTH WIZARD ===")
print("Keys are hidden and encrypted with Windows DPAPI.")
consumer_key = getpass.getpass(
    "Sandbox Consumer Key: "
).strip()
consumer_secret = getpass.getpass(
    "Sandbox Consumer Secret: "
).strip()
if not consumer_key or not consumer_secret:
    raise SystemExit("Key and Secret are required.")

flow = ETradeOAuthFlow(
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
)
print("Requesting temporary token...")
request_pair = flow.request_token()
url = flow.authorization_url(
    request_pair.token
)
print("Approve access in the browser and copy the code:")
print(url)
webbrowser.open(url, new=1)
verifier = input(
    "Verification Code: "
).strip()
if not verifier:
    raise SystemExit("Verification code is required.")

access_pair = flow.access_token(
    request_token=request_pair.token,
    request_token_secret=request_pair.secret,
    verifier=verifier,
)
ETradeCredentialVault(VAULT).save({
    "environment": "SANDBOX",
    "consumer_key": consumer_key,
    "consumer_secret": consumer_secret,
    "access_token": access_pair.token,
    "access_token_secret": access_pair.secret,
    "created_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "revoked": False,
})
print("OAUTH COMPLETE")
print(f"Encrypted vault: {VAULT}")
print(json.dumps({
    "consumer_key": mask(consumer_key),
    "access_token": mask(access_pair.token),
    "environment": "SANDBOX",
}, indent=2))
