from __future__ import annotations
from typing import Any

from broker_abstraction.base import ReadOnlyBrokerAdapter
from broker_abstraction.models import (
    UniversalAccount,
    UniversalOrder,
    UniversalPosition,
    UniversalQuote,
)


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class AlpacaReadOnlyAdapter(ReadOnlyBrokerAdapter):
    broker_name = "ALPACA"
    environment = "PAPER"

    def __init__(self, snapshot: dict[str, Any]) -> None:
        self.snapshot = snapshot

    def accounts(self) -> list[dict]:
        item = self.snapshot.get("account") or {}
        if not item:
            return []
        return [
            UniversalAccount(
                broker="ALPACA",
                environment="PAPER",
                account_id=str(item.get("id") or ""),
                account_id_masked=str(item.get("account_number") or ""),
                account_type="BROKERAGE",
                account_mode=str(
                    item.get("status") or "PAPER"
                ),
                status=str(item.get("status") or ""),
                cash=_float(item.get("cash")),
                buying_power=_float(item.get("buying_power")),
                equity=_float(item.get("equity")),
                market_value=_float(
                    item.get("long_market_value")
                ),
                raw=item,
            ).to_dict()
        ]

    def positions(self) -> list[dict]:
        account_id = str(
            (self.snapshot.get("account") or {}).get("id")
            or ""
        )
        result = []
        for item in self.snapshot.get("positions", []):
            quantity = _float(item.get("qty")) or 0.0
            result.append(
                UniversalPosition(
                    broker="ALPACA",
                    environment="PAPER",
                    account_id=account_id,
                    symbol=str(item.get("symbol") or ""),
                    security_type=str(
                        item.get("asset_class") or "EQ"
                    ),
                    side=str(
                        item.get("side")
                        or ("SHORT" if quantity < 0 else "LONG")
                    ).upper(),
                    quantity=quantity,
                    average_price=_float(
                        item.get("avg_entry_price")
                    ),
                    market_price=_float(
                        item.get("current_price")
                    ),
                    market_value=_float(
                        item.get("market_value")
                    ),
                    cost_basis=_float(
                        item.get("cost_basis")
                    ),
                    unrealized_pl=_float(
                        item.get("unrealized_pl")
                    ),
                    unrealized_pl_percent=_float(
                        item.get("unrealized_plpc")
                    ),
                    day_pl=_float(
                        item.get("unrealized_intraday_pl")
                    ),
                    day_pl_percent=_float(
                        item.get("unrealized_intraday_plpc")
                    ),
                    raw=item,
                ).to_dict()
            )
        return result

    def orders(self) -> list[dict]:
        account_id = str(
            (self.snapshot.get("account") or {}).get("id")
            or ""
        )
        result = []
        for item in self.snapshot.get("orders", []):
            result.append(
                UniversalOrder(
                    broker="ALPACA",
                    environment="PAPER",
                    account_id=account_id,
                    order_id=str(item.get("id") or ""),
                    symbol=str(item.get("symbol") or ""),
                    security_type=str(
                        item.get("asset_class") or "EQ"
                    ),
                    side=str(item.get("side") or "").upper(),
                    order_type=str(item.get("type") or ""),
                    time_in_force=str(
                        item.get("time_in_force") or ""
                    ),
                    status=str(item.get("status") or ""),
                    quantity=_float(item.get("qty")) or 0.0,
                    filled_quantity=_float(
                        item.get("filled_qty")
                    ) or 0.0,
                    limit_price=_float(
                        item.get("limit_price")
                    ),
                    stop_price=_float(
                        item.get("stop_price")
                    ),
                    average_fill_price=_float(
                        item.get("filled_avg_price")
                    ),
                    submitted_at=item.get("submitted_at"),
                    executed_at=item.get("filled_at"),
                    raw=item,
                ).to_dict()
            )
        return result

    def quotes(self, symbols: list[str]) -> list[dict]:
        result = []
        quotes = self.snapshot.get("quotes", {})
        for symbol in symbols:
            item = quotes.get(symbol) or quotes.get(symbol.upper())
            if not item:
                continue
            result.append(
                UniversalQuote(
                    broker="ALPACA",
                    environment="PAPER",
                    symbol=symbol.upper(),
                    security_type="EQ",
                    bid=_float(item.get("bid_price")),
                    ask=_float(item.get("ask_price")),
                    last=_float(
                        item.get("last_price")
                        or item.get("price")
                    ),
                    open=_float(item.get("open")),
                    high=_float(item.get("high")),
                    low=_float(item.get("low")),
                    previous_close=_float(
                        item.get("previous_close")
                    ),
                    volume=_float(item.get("volume")),
                    timestamp=item.get("timestamp"),
                    status=str(item.get("status") or ""),
                    raw=item,
                ).to_dict()
            )
        return result
