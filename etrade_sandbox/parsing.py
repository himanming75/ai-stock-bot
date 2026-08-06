from __future__ import annotations


def extract_accounts(response: dict) -> list[dict]:
    data = response.get("data") or {}
    root = data.get(
        "AccountListResponse"
    ) or {}
    accounts = (
        (root.get("Accounts") or {})
        .get("Account", [])
    )
    if isinstance(accounts, dict):
        accounts = [accounts]
    return [
        {
            "account_id_key": item.get(
                "accountIdKey"
            ),
            "account_id_masked": item.get(
                "accountId"
            ),
            "account_type": item.get(
                "accountType"
            ),
            "account_mode": item.get(
                "accountMode"
            ),
            "institution_type": item.get(
                "institutionType"
            ),
            "status": item.get(
                "accountStatus"
            ),
        }
        for item in accounts
        if isinstance(item, dict)
    ]
