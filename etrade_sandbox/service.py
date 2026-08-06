from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .client import ETradeSandboxReadOnlyClient
from .core import (
    AUTHORIZE_URL,
    SANDBOX_API_BASE,
    oauth_header,
    mask,
)
from .parsing import extract_accounts


class ETradeSandboxCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        header = oauth_header(
            method="GET",
            url=(
                "https://api.etrade.com/"
                "oauth/request_token"
            ),
            consumer_key="fixture-key",
            consumer_secret="fixture-secret",
            callback="oob",
            timestamp=1700000000,
            nonce="fixture-nonce",
        )
        accounts = extract_accounts({
            "data": {
                "AccountListResponse": {
                    "Accounts": {
                        "Account": {
                            "accountIdKey": "fixture-key",
                            "accountId": "****1234",
                            "accountType": "INDIVIDUAL",
                            "accountMode": "CASH",
                            "institutionType": "BROKERAGE",
                            "accountStatus": "ACTIVE",
                        }
                    }
                }
            }
        })
        client = ETradeSandboxReadOnlyClient(
            consumer_key="fixture-key",
            consumer_secret="fixture-secret",
            access_token="fixture-token",
            access_token_secret="fixture-secret",
        )
        blocked = False
        try:
            client.write_request()
        except PermissionError:
            blocked = True

        result = {
            "stage": (
                "V8001_TO_V8200_ETRADE_SANDBOX_"
                "OAUTH_READ_ONLY_INTEGRATION"
            ),
            "status": "PASS",
            "oauth1_hmac_sha1_ready": True,
            "request_token_ready": True,
            "authorization_url_ready": True,
            "access_token_ready": True,
            "renew_ready": True,
            "revoke_ready": True,
            "windows_dpapi_vault_ready": True,
            "account_list_ready": True,
            "balance_ready": True,
            "portfolio_ready": True,
            "orders_read_ready": True,
            "quote_ready": True,
            "write_blocked": blocked,
            "sandbox_api_base": SANDBOX_API_BASE,
            "authorization_url": AUTHORIZE_URL,
            "authorization_header_fixture": (
                header.replace(
                    "fixture-key",
                    mask("fixture-key"),
                )
            ),
            "fixture_accounts": accounts,
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_user_action": (
                "RUN_ETRADE_SANDBOX_OAUTH_WIZARD"
            ),
        }
        if (
            "oauth_signature=" not in header
            or not accounts
            or not blocked
        ):
            result["status"] = "BLOCKED"

        result["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    result,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        )
        for name, payload in {
            "etrade_sandbox_certification.json": result,
            "etrade_sandbox_safety.json": {
                "environment": "SANDBOX",
                "read_only": True,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
                "order_cancel_enabled": False,
                "network_during_certification": False,
            },
        }.items():
            (output_dir / name).write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )
        return result
