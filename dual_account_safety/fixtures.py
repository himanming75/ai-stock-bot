from __future__ import annotations
from .models import AccountProfile


ALPACA_PAPER = AccountProfile(
    account_key="ALPACA_PAPER_PRIMARY",
    broker="ALPACA",
    environment="PAPER",
    role="PAPER_EXECUTION",
    alias="Alpaca Paper",
    read_enabled=True,
    write_enabled=False,
    strategy_execution_enabled=True,
    kill_switch_active=False,
    actual_connection_validated=True,
    metadata={
        "purpose": "STRATEGY_TESTING",
        "submission_requires_separate_approval": True,
    },
)

ETRADE_PRIMARY = AccountProfile(
    account_key="ETRADE_PRIMARY",
    broker="ETRADE",
    environment="PRODUCTION",
    role="ACTUAL_READ_ONLY",
    alias="E*TRADE Primary",
    read_enabled=True,
    write_enabled=False,
    strategy_execution_enabled=False,
    kill_switch_active=False,
    actual_connection_validated=False,
    metadata={
        "purpose": "ACTUAL_ASSET_VISIBILITY",
        "key_issuance_pending": True,
    },
)

SNAPSHOTS = [
    {
        "account_key": "ALPACA_PAPER_PRIMARY",
        "broker": "ALPACA",
        "environment": "PAPER",
        "equity": "100014.45",
        "cash": "92000.00",
        "unrealized_pl": "14.45",
    },
    {
        "account_key": "ETRADE_PRIMARY",
        "broker": "ETRADE",
        "environment": "PRODUCTION",
        "equity": "0",
        "cash": "0",
        "unrealized_pl": "0",
        "external_validation_pending": True,
    },
]
