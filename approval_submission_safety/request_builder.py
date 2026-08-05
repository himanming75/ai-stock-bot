from __future__ import annotations

from .crypto import fingerprint


def build_broker_request(ticket: dict) -> dict:
    payload = dict(ticket.get("payload", {}))
    request = {
        "method": "POST",
        "url": "https://paper-api.alpaca.markets/v2/orders",
        "headers": {
            "Content-Type": "application/json",
            "Idempotency-Key": ticket.get("idempotency_key"),
        },
        "json": payload,
        "submission_enabled": False,
        "broker_write_allowed": False,
    }
    return {
        "request": request,
        "request_fingerprint": fingerprint(request),
        "network_call_performed": False,
        "broker_write_performed": False,
    }
