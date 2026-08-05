from __future__ import annotations
import hashlib
import json


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def build_submission_envelope(item: dict) -> dict:
    broker_request = item.get("broker_request", {})
    request = broker_request.get("request", {})
    envelope = {
        "engine_mode": "DRY_RUN_ONLY",
        "ticket_id": item.get("ticket_id"),
        "idempotency_key": item.get("idempotency_key"),
        "method": request.get("method"),
        "url": request.get("url"),
        "headers": request.get("headers", {}),
        "json": request.get("json", {}),
        "approval_status": item.get("status"),
        "submission_enabled": False,
        "broker_write_allowed": False,
        "network_call_allowed": False,
    }
    return {
        "submission_id": f"submit_{fingerprint(envelope)[:24]}",
        "submission_fingerprint": fingerprint(envelope),
        "envelope": envelope,
        "actual_network_call_performed": False,
        "actual_broker_write_performed": False,
    }
