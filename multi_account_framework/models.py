from __future__ import annotations

import re

ACCOUNT_ALIAS_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,31}$")
SUPPORTED_BROKERS = {"alpaca", "etrade", "ibkr", "schwab"}
SUPPORTED_MODES = {"paper", "sandbox", "disabled"}


def validate_alias(alias: str) -> bool:
    return bool(ACCOUNT_ALIAS_PATTERN.fullmatch(alias or ""))


def ledger_namespace(alias: str) -> str:
    return f"accounts/{alias}"
