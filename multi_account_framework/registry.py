from __future__ import annotations

from .adapters import adapter_for
from .models import (
    SUPPORTED_BROKERS,
    SUPPORTED_MODES,
    ledger_namespace,
    validate_alias,
)


def validate_account(account: dict) -> list[str]:
    blockers = []
    alias = str(account.get("alias", ""))
    broker = str(account.get("broker", "")).lower()
    mode = str(account.get("mode", "")).lower()

    if not validate_alias(alias):
        blockers.append("ACCOUNT_ALIAS_INVALID")
    if broker not in SUPPORTED_BROKERS:
        blockers.append("BROKER_NOT_SUPPORTED")
    if mode not in SUPPORTED_MODES:
        blockers.append("ACCOUNT_MODE_INVALID")
    if account.get("enabled") is True:
        blockers.append("ACCOUNT_ENABLEMENT_HARD_DISABLED")
    if account.get("broker_network_enabled") is True:
        blockers.append("BROKER_NETWORK_MUST_BE_OFF")
    if account.get("order_submission_enabled") is True:
        blockers.append("ORDER_SUBMISSION_MUST_BE_OFF")
    if not account.get("credential_aliases"):
        blockers.append("CREDENTIAL_ALIAS_MAPPING_MISSING")
    return blockers


def normalize_account(account: dict) -> dict:
    alias = str(account.get("alias", ""))
    broker = str(account.get("broker", "")).lower()
    adapter = adapter_for(broker)
    return {
        "alias": alias,
        "display_name": account.get("display_name", alias),
        "broker": broker,
        "mode": str(account.get("mode", "disabled")).lower(),
        "enabled": False,
        "broker_network_enabled": False,
        "order_submission_enabled": False,
        "credential_aliases": dict(
            account.get("credential_aliases", {})
        ),
        "risk_policy": dict(account.get("risk_policy", {})),
        "controller_profile": dict(
            account.get("controller_profile", {})
        ),
        "ledger_namespace": ledger_namespace(alias),
        "adapter_capabilities": adapter.capabilities(),
        "metadata": dict(account.get("metadata", {})),
    }
