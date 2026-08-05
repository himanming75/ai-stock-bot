from __future__ import annotations
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BrokerCapabilities:
    broker: str
    account_read: bool
    positions_read: bool
    orders_read: bool
    market_data_read: bool
    paper_trading: bool
    order_submission: bool
    order_cancel: bool
    fractional_shares: bool
    extended_hours: bool
    options: bool
    streaming: bool

    def to_dict(self) -> dict:
        return asdict(self)
