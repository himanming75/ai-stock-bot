from __future__ import annotations
from typing import Any


PHRASE_ONE = "I_UNDERSTAND_THIS_IS_LIVE_TRADING"
PHRASE_TWO = "I_ACCEPT_REAL_FINANCIAL_LOSS_RISK"


def evaluate_confirmation(
    *,
    confirmation_one: str,
    confirmation_two: str,
    live_network_enabled: bool,
    live_write_enabled: bool,
) -> dict[str, Any]:
    checks = {
        "confirmation_one_absent": confirmation_one == "",
        "confirmation_two_absent": confirmation_two == "",
        "live_network_disabled": live_network_enabled is False,
        "live_write_disabled": live_write_enabled is False,
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "live_activation_allowed": False,
        "valid": all(checks.values()),
    }
