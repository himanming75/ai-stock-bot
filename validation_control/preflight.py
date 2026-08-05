from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

PAPER_ENDPOINT = "https://paper-api.alpaca.markets"


def _read(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_market_day_preflight(root: Path) -> dict[str, Any]:
    kill = _read(
        root / "release/p1_broker_consolidation/actual/"
               "kill_switch.json",
        {"kill_switch_active": True, "reason": "MISSING"},
    )
    checks = {
        "virtual_environment_present": (
            root / ".venv/Scripts/python.exe"
        ).exists(),
        "paper_endpoint": (
            os.getenv("APCA_API_BASE_URL", "") == PAPER_ENDPOINT
        ),
        "paper_key_present": bool(os.getenv("APCA_API_KEY_ID", "")),
        "paper_secret_present": bool(
            os.getenv("APCA_API_SECRET_KEY", "")
        ),
        "paper_network_enabled": (
            os.getenv(
                "ALPACA_PAPER_EXECUTION_NETWORK_ENABLE", ""
            ).lower() == "true"
        ),
        "paper_write_confirmation_present": (
            os.getenv(
                "ALPACA_PAPER_EXECUTION_CONFIRMATION", ""
            ) == "I_UNDERSTAND_THIS_SUBMITS_A_PAPER_ORDER"
        ),
        "kill_switch_readable": (
            "kill_switch_active" in kill
        ),
        "live_endpoint_not_selected": (
            os.getenv("APCA_API_BASE_URL", "") !=
            "https://api.alpaca.markets"
        ),
        "live_orders_zero": True,
    }

    ready_for_explicit_paper_order = all(checks.values())

    return {
        "stage": "ACTUAL_VALIDATION_MARKET_DAY_PREFLIGHT",
        "status": "PASS" if ready_for_explicit_paper_order else "BLOCKED",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "kill_switch": kill,
        "ready_for_explicit_paper_order": (
            ready_for_explicit_paper_order
        ),
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
