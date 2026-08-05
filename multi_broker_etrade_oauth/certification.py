from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import OAuthAccessToken
from .session import ETradeOAuthSessionManager
from .storage import JsonTokenStore
from .transport import FixtureOAuthTransport
from .workflow import ETradeOAuthWorkflow


def certify(output_dir: Path) -> dict:
    responses = {
        ETradeOAuthWorkflow.REQUEST_TOKEN_URL: (
            "oauth_token=req-token&oauth_token_secret=req-secret&"
            "oauth_callback_confirmed=true"
        ),
        ETradeOAuthWorkflow.ACCESS_TOKEN_URL: (
            "oauth_token=access-token&oauth_token_secret=access-secret"
        ),
        ETradeOAuthWorkflow.RENEW_TOKEN_URL: (
            "oauth_token=access-token&renewed=true"
        ),
        ETradeOAuthWorkflow.REVOKE_TOKEN_URL: (
            "revoked=true"
        ),
    }
    transport = FixtureOAuthTransport(responses)
    workflow = ETradeOAuthWorkflow(
        consumer_key="fixture-consumer-key",
        consumer_secret="fixture-consumer-secret",
        transport=transport,
    )

    request_token = workflow.request_token()
    authorization_url = workflow.authorization_url(request_token)
    access_token = workflow.access_token(
        request_token,
        verifier="fixture-verifier",
        environment="SANDBOX",
    )

    store = JsonTokenStore(output_dir / "fixture_session_state.json")
    manager = ETradeOAuthSessionManager(store)
    manager.save_request_token(request_token)
    request_state = manager.state()
    manager.save_access_token(access_token)

    now = datetime.now(timezone.utc)
    active_state = manager.state(
        now=now,
        last_activity_utc=now - timedelta(minutes=30),
    )
    inactive_state = manager.state(
        now=now,
        last_activity_utc=now - timedelta(hours=3),
    )

    renewed = workflow.renew(access_token)
    revoked = workflow.revoke(access_token)
    if revoked:
        manager.mark_revoked()
    revoked_state = manager.state()

    result = {
        "stage": "V3601_TO_V3800_ETRADE_OAUTH_SESSION_SANDBOX_READ_VALIDATION",
        "status": "PASS",
        "generated_at": now.isoformat(),
        "request_token_received": bool(request_token.oauth_token),
        "callback_confirmed": request_token.callback_confirmed,
        "authorization_url_generated": authorization_url.startswith(
            ETradeOAuthWorkflow.AUTHORIZE_URL
        ),
        "access_token_received": bool(access_token.oauth_token),
        "request_state": request_state.to_dict(),
        "active_state": active_state.to_dict(),
        "inactive_state": inactive_state.to_dict(),
        "renew_succeeded": renewed,
        "revoke_succeeded": revoked,
        "revoked_state": revoked_state.to_dict(),
        "oauth_call_count": len(transport.calls),
        "oauth_calls": [
            {"url": item["url"], "authorization_header_present": (
                "Authorization" in item["headers"]
            )}
            for item in transport.calls
        ],
        "sandbox_adapter_builder_present": True,
        "actual_sandbox_network_validation_performed": False,
        "fixture_transport_used": True,
        "real_credentials_used": False,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "existing_alpaca_controller_modified": False,
        "existing_market_polling_modified": False,
        "next_user_action": (
            "OBTAIN_ETRADE_SANDBOX_CONSUMER_KEY_AND_RUN_EXPLICIT_SANDBOX_READ"
        ),
        "next_fixed_development": (
            "V3801_TO_V4000_ETRADE_SANDBOX_ACCOUNT_READ_CERTIFICATION"
        ),
    }

    checks = [
        result["request_token_received"],
        result["callback_confirmed"],
        result["authorization_url_generated"],
        result["access_token_received"],
        result["renew_succeeded"],
        result["revoke_succeeded"],
        result["revoked_state"]["revoked"],
    ]
    if not all(checks):
        result["status"] = "BLOCKED"

    seed = dict(result)
    seed.pop("generated_at")
    result["certification_fingerprint"] = hashlib.sha256(
        json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in {
        "etrade_oauth_session_certification.json": result,
        "etrade_oauth_workflow_report.json": {
            "request_token_received": result["request_token_received"],
            "callback_confirmed": result["callback_confirmed"],
            "authorization_url_generated": result[
                "authorization_url_generated"
            ],
            "access_token_received": result["access_token_received"],
            "renew_succeeded": result["renew_succeeded"],
            "revoke_succeeded": result["revoke_succeeded"],
        },
        "etrade_sandbox_read_readiness.json": {
            "sandbox_adapter_builder_present": True,
            "actual_sandbox_network_validation_performed": False,
            "real_credentials_used": False,
            "next_user_action": result["next_user_action"],
        },
    }.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    with (output_dir / "etrade_oauth_session_ledger.jsonl").open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(json.dumps(result, sort_keys=True) + "\n")

    store.clear()
    return result
