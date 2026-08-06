from __future__ import annotations
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from .plans import get_plan


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_subscription_fixture(
    *,
    user_id: str,
    plan: str,
) -> dict:
    item = get_plan(plan)
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=30)
    return {
        "subscription_id": f"sub_{secrets.token_hex(8)}",
        "user_id": user_id,
        "plan": plan.upper(),
        "status": "ACTIVE",
        "current_period_start": now.isoformat(),
        "current_period_end": end.isoformat(),
        "trial_end": None,
        "cancel_at_period_end": False,
        "external_provider": None,
        "external_customer_id": None,
        "external_subscription_id": None,
        "monthly_price_usd": item["monthly_price_usd"],
        "external_charge_performed": False,
    }


def create_invoice_fixture(
    *,
    user_id: str,
    subscription: dict,
) -> dict:
    price = get_plan(
        subscription["plan"]
    )["monthly_price_usd"]
    now = datetime.now(timezone.utc)
    return {
        "invoice_id": f"inv_{secrets.token_hex(8)}",
        "user_id": user_id,
        "subscription_id": subscription[
            "subscription_id"
        ],
        "amount_due_usd": float(price),
        "amount_paid_usd": 0.0,
        "status": "DRAFT",
        "line_items": [
            {
                "description": (
                    f"{subscription['plan']} monthly plan"
                ),
                "quantity": 1,
                "unit_price_usd": float(price),
            }
        ],
        "issued_at": now.isoformat(),
        "due_at": (
            now + timedelta(days=7)
        ).isoformat(),
        "paid_at": None,
        "external_payment_performed": False,
    }


def generate_license(
    *,
    user_id: str,
    plan: str,
    machine_limit: int,
    expires_days: int = 365,
) -> dict:
    raw_key = (
        "LIC-"
        + secrets.token_hex(4).upper()
        + "-"
        + secrets.token_hex(4).upper()
        + "-"
        + secrets.token_hex(4).upper()
    )
    return {
        "license_id": f"lic_{secrets.token_hex(8)}",
        "user_id": user_id,
        "plan": plan.upper(),
        "machine_limit": machine_limit,
        "expires_at": (
            datetime.now(timezone.utc)
            + timedelta(days=expires_days)
        ).isoformat(),
        "license_key": raw_key,
        "license_key_hash": hashlib.sha256(
            raw_key.encode("utf-8")
        ).hexdigest(),
        "plaintext_storage_allowed": False,
    }
