from __future__ import annotations


ACCOUNTS = [
    {
        "account_key": "ALPACA_PAPER_PRIMARY",
        "alias": "Alpaca Paper",
        "broker": "ALPACA",
        "environment": "PAPER",
        "role": "PAPER_EXECUTION",
        "health_status": "HEALTHY",
        "actual_connection_validated": True,
        "key_issuance_pending": False,
        "equity": "100014.45",
        "cash": "92000.00",
        "unrealized_pl": "14.45",
    },
    {
        "account_key": "ETRADE_PRIMARY",
        "alias": "E*TRADE Primary",
        "broker": "ETRADE",
        "environment": "PRODUCTION",
        "role": "ACTUAL_READ_ONLY",
        "health_status": "BLOCKED_PENDING_KEYS",
        "actual_connection_validated": False,
        "key_issuance_pending": True,
        "equity": "0",
        "cash": "0",
        "unrealized_pl": "0",
    },
]
