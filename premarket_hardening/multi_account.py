from __future__ import annotations


ALLOWED_ROLES = {
    "PAPER_EXECUTION",
    "ACTUAL_READ_ONLY",
    "MONITOR_ONLY",
}


def validate_accounts(accounts: list[dict]) -> dict:
    issues = []
    seen = set()

    for account in accounts:
        key = account.get("account_key")
        if not key:
            issues.append("MISSING_ACCOUNT_KEY")
            continue
        if key in seen:
            issues.append(f"DUPLICATE_ACCOUNT_KEY:{key}")
        seen.add(key)

        if account.get("role") not in ALLOWED_ROLES:
            issues.append(f"INVALID_ROLE:{key}")

        if (
            account.get("environment") == "PRODUCTION"
            and account.get("write_enabled")
        ):
            issues.append(f"PRODUCTION_WRITE_NOT_ALLOWED:{key}")

        if account.get("risk_limit", 0) <= 0:
            issues.append(f"INVALID_RISK_LIMIT:{key}")

    return {
        "status": "PASS" if not issues else "BLOCKED",
        "account_count": len(accounts),
        "unique_account_count": len(seen),
        "issues": issues,
        "future_multi_account_ready": not issues,
    }


def fixture_accounts(count: int = 10) -> list[dict]:
    accounts = []
    for index in range(count):
        paper = index % 2 == 0
        accounts.append({
            "account_key": f"ACCOUNT_{index:02d}",
            "broker": "ALPACA" if paper else "ETRADE",
            "environment": "PAPER" if paper else "PRODUCTION",
            "role": (
                "PAPER_EXECUTION"
                if paper
                else "ACTUAL_READ_ONLY"
            ),
            "write_enabled": False,
            "risk_limit": 0.01,
            "strategy_assignment": (
                "MOMENTUM"
                if paper
                else "MONITOR_ONLY"
            ),
        })
    return accounts
