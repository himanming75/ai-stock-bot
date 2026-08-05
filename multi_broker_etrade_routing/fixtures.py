from __future__ import annotations


ACCOUNTS = [
    {
        "accountId": "****6728",
        "accountIdKey": "individual-brokerage-key",
        "accountMode": "MARGIN",
        "accountStatus": "ACTIVE",
        "accountType": "INDIVIDUAL",
    },
    {
        "accountId": "****2368",
        "accountIdKey": "stock-plan-key",
        "accountMode": "CASH",
        "accountStatus": "ACTIVE",
        "accountType": "STOCK_PLAN",
    },
    {
        "accountId": "****9999",
        "accountIdKey": "closed-account-key",
        "accountMode": "CASH",
        "accountStatus": "CLOSED",
        "accountType": "INDIVIDUAL",
    },
]

ACCOUNT_SNAPSHOTS = {
    "individual-brokerage-key": {
        "broker": "ETRADE",
        "account_id": "individual-brokerage-key",
        "currency": "USD",
        "equity": "100500.75",
        "cash": "25000.50",
        "buying_power": "25000.50",
        "status": "ACTIVE",
    },
    "stock-plan-key": {
        "broker": "ETRADE",
        "account_id": "stock-plan-key",
        "currency": "USD",
        "equity": "32500.00",
        "cash": "500.00",
        "buying_power": "500.00",
        "status": "ACTIVE",
    },
}
