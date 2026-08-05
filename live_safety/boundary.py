from __future__ import annotations
import os
from pathlib import Path
from typing import Any

from .confirmation_gate import evaluate_confirmation
from .credential_guard import evaluate_credentials
from .kill_switch import ensure_live_kill_switch
from .paper_completion_gate import evaluate_paper_completion
from .risk_policy import LiveRiskPolicy


PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"


def evaluate_live_boundary(root: Path) -> dict[str, Any]:
    credentials = evaluate_credentials(
        paper_key=os.getenv("APCA_API_KEY_ID", ""),
        paper_secret=os.getenv("APCA_API_SECRET_KEY", ""),
        live_key=os.getenv("LIVE_APCA_API_KEY_ID", ""),
        live_secret=os.getenv("LIVE_APCA_API_SECRET_KEY", ""),
    )
    kill_switch = ensure_live_kill_switch(
        root / "release/l1_live_safety_boundary/actual/"
               "live_kill_switch.json"
    )
    risk = LiveRiskPolicy(
        maximum_order_notional=float(
            os.getenv("LIVE_MAX_ORDER_NOTIONAL", "10")
        ),
        maximum_daily_orders=int(
            os.getenv("LIVE_MAX_DAILY_ORDERS", "1")
        ),
        maximum_daily_loss=float(
            os.getenv("LIVE_MAX_DAILY_LOSS", "10")
        ),
        maximum_total_exposure=float(
            os.getenv("LIVE_MAX_TOTAL_EXPOSURE", "25")
        ),
        maximum_position_count=int(
            os.getenv("LIVE_MAX_POSITION_COUNT", "1")
        ),
        allowed_symbols=tuple(
            x.strip().upper()
            for x in os.getenv("LIVE_ALLOWED_SYMBOLS", "SPY").split(",")
            if x.strip()
        ),
        allowed_account_ids=tuple(
            x.strip()
            for x in os.getenv("LIVE_ALLOWED_ACCOUNT_IDS", "").split(",")
            if x.strip()
        ),
    ).evaluate()
    confirmation = evaluate_confirmation(
        confirmation_one=os.getenv("LIVE_CONFIRMATION_ONE", ""),
        confirmation_two=os.getenv("LIVE_CONFIRMATION_TWO", ""),
        live_network_enabled=False,
        live_write_enabled=False,
    )
    paper_completion = evaluate_paper_completion(root)

    checks = {
        "paper_endpoint_valid": (
            os.getenv("APCA_API_BASE_URL", PAPER_URL) == PAPER_URL
        ),
        "live_endpoint_valid": (
            os.getenv("LIVE_APCA_API_BASE_URL", LIVE_URL) == LIVE_URL
        ),
        "credentials_safe": credentials["valid"],
        "live_kill_switch_active": (
            kill_switch.get("live_kill_switch_active") is True
        ),
        "risk_policy_safe": risk["valid"],
        "confirmation_gate_safe": confirmation["valid"],
        "paper_completion_gate_present": True,
    }

    return {
        "stage": "L1",
        "state": "LIVE_SAFETY_BOUNDARY_PREPARED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "credentials": credentials,
        "live_kill_switch": kill_switch,
        "risk_policy": risk,
        "confirmation_gate": confirmation,
        "paper_completion": paper_completion,
        "live_read_only_allowed": False,
        "live_activation_allowed": False,
        "live_network_enabled": False,
        "live_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_stage": (
            "L2_LIVE_READ_ONLY_QUALIFICATION_AFTER_PAPER_COMPLETE"
        ),
    }
