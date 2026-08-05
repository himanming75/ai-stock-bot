from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .models import AccountDefinition


def load_account_registry(path: Path) -> list[AccountDefinition]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    accounts = []
    for item in value.get("accounts", []):
        account = AccountDefinition(
            account_id=str(item.get("account_id", "")).strip(),
            broker_id=str(item.get("broker_id", "")).strip().lower(),
            broker_mode=str(item.get("broker_mode", "")).strip().lower(),
            profile_name=str(item.get("profile_name", "")).strip(),
            enabled=item.get("enabled") is True,
            allocation_weight=Decimal(
                str(item.get("allocation_weight", "0"))
            ),
            maximum_account_notional=Decimal(
                str(item.get("maximum_account_notional", "0"))
            ),
            credential_vault_mode=str(
                item.get("credential_vault_mode", "")
            ).strip().lower(),
            tags=tuple(str(tag) for tag in item.get("tags", [])),
        )
        accounts.append(account)
    return accounts


def validate_account_registry(
    accounts: list[AccountDefinition],
) -> dict[str, Any]:
    ids = [account.account_id for account in accounts]
    enabled = [account for account in accounts if account.enabled]
    checks = {
        "accounts_present": bool(accounts),
        "account_ids_unique": len(ids) == len(set(ids)),
        "all_accounts_valid": all(
            account.validate()["valid"] for account in accounts
        ),
        "enabled_accounts_present": bool(enabled),
        "allocation_weight_total_safe": (
            sum(
                account.allocation_weight
                for account in enabled
            ) <= Decimal("1")
        ),
        "live_accounts_disabled_in_preparation": all(
            account.broker_mode != "live" or account.enabled is False
            for account in accounts
        ),
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "valid": all(checks.values()),
        "account_count": len(accounts),
        "enabled_account_count": len(enabled),
        "accounts": [account.as_json() for account in accounts],
    }
