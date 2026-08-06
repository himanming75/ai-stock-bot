from __future__ import annotations
from datetime import datetime, timezone
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


def _timestamp(value):
    if value in (None, ""):
        return None
    try:
        number = float(value)
        if number > 10_000_000_000:
            number /= 1000
        return datetime.fromtimestamp(
            number,
            tz=timezone.utc,
        ).isoformat()
    except Exception:
        return str(value)


class ETradeReadOnlyAdapter(ReadOnlyBrokerAdapter):
    broker_name = "ETRADE"
    environment = "SANDBOX"

    def __init__(self, snapshot: dict[str, Any]) -> None:
        self.snapshot = snapshot

    def accounts(self) -> list[dict]:
        result = []
        for item in self.snapshot.get("accounts", []):
            account_id = str(
                item.get("account_id_key")
                or item.get("accountIdKey")
                or ""
            )
            result.append(
                UniversalAccount(
                    broker="ETRADE",
                    environment="SANDBOX",
                    account_id=account_id,
                    account_id_masked=str(
                        item.get("account_id_masked")
                        or item.get("accountId")
                        or ""
                    ),
                    account_type=str(
                        item.get("account_type")
                        or item.get("accountType")
                        or ""
                    ),
                    account_mode=str(
                        item.get("account_mode")
                        or item.get("accountMode")
                        or ""
                    ),
                    status=str(
                        item.get("status")
                        or item.get("accountStatus")
                        or ""
                    ),
                    raw=item,
                ).to_dict()
            )
        return result

    def positions(self) -> list[dict]:
        result = []
        portfolios = self.snapshot.get("portfolios", {})
        for account_id, response in portfolios.items():
            data = response.get("data") or {}
            roots = (
                (data.get("PortfolioResponse") or {})
                .get("AccountPortfolio", [])
            )
            if isinstance(roots, dict):
                roots = [roots]
            for root in roots or []:
                positions = root.get("Position", [])
                if isinstance(positions, dict):
                    positions = [positions]
                for item in positions or []:
                    product = item.get("Product") or {}
                    quick = item.get("Quick") or {}
                    quantity = _float(item.get("quantity")) or 0.0
                    result.append(
                        UniversalPosition(
                            broker="ETRADE",
                            environment="SANDBOX",
                            account_id=str(account_id),
                            symbol=str(
                                product.get("symbol")
                                or (product.get("productId") or {}).get("symbol")
                                or item.get("symbolDescription")
                                or ""
                            ),
                            security_type=str(
                                product.get("securityType") or ""
                            ),
                            side=(
                                "SHORT"
                                if quantity < 0
                                else str(
                                    item.get("positionType")
                                    or "LONG"
                                )
                            ),
                            quantity=quantity,
                            average_price=_float(
                                item.get("pricePaid")
                                or item.get("costPerShare")
                            ),
                            market_price=_float(
                                quick.get("lastTrade")
                            ),
                            market_value=_float(
                                item.get("marketValue")
                            ),
                            cost_basis=_float(
                                item.get("totalCost")
                            ),
                            unrealized_pl=_float(
                                item.get("totalGain")
                            ),
                            unrealized_pl_percent=_float(
                                item.get("totalGainPct")
                            ),
                            day_pl=_float(
                                item.get("daysGain")
                            ),
                            day_pl_percent=_float(
                                item.get("daysGainPct")
                            ),
                            raw=item,
                        ).to_dict()
                    )
        return result

    def orders(self) -> list[dict]:
        result = []
        orders_map = self.snapshot.get("orders", {})
        for account_id, response in orders_map.items():
            data = response.get("data") or {}
            orders = (
                (data.get("OrdersResponse") or {})
                .get("Order", [])
            )
            if isinstance(orders, dict):
                orders = [orders]
            for order in orders or []:
                details = order.get("OrderDetail", [])
                if isinstance(details, dict):
                    details = [details]
                for detail in details or []:
                    instruments = detail.get("Instrument", [])
                    if isinstance(instruments, dict):
                        instruments = [instruments]
                    for instrument in instruments or []:
                        product = instrument.get("Product") or {}
                        result.append(
                            UniversalOrder(
                                broker="ETRADE",
                                environment="SANDBOX",
                                account_id=str(account_id),
                                order_id=str(
                                    order.get("orderId") or ""
                                ),
                                symbol=str(
                                    product.get("symbol")
                                    or (product.get("productId") or {}).get("symbol")
                                    or ""
                                ),
                                security_type=str(
                                    product.get("securityType") or ""
                                ),
                                side=str(
                                    instrument.get("orderAction") or ""
                                ),
                                order_type=str(
                                    order.get("orderType")
                                    or detail.get("priceType")
                                    or ""
                                ),
                                time_in_force=str(
                                    detail.get("orderTerm") or ""
                                ),
                                status=str(
                                    detail.get("status") or ""
                                ),
                                quantity=_float(
                                    instrument.get("orderedQuantity")
                                ) or 0.0,
                                filled_quantity=_float(
                                    instrument.get("filledQuantity")
                                ) or 0.0,
                                limit_price=_float(
                                    detail.get("limitPrice")
                                ),
                                stop_price=_float(
                                    detail.get("stopPrice")
                                ),
                                average_fill_price=_float(
                                    instrument.get("averageExecutionPrice")
                                ),
                                submitted_at=_timestamp(
                                    detail.get("placedTime")
                                ),
                                executed_at=_timestamp(
                                    detail.get("executedTime")
                                ),
                                raw={
                                    "order": order,
                                    "detail": detail,
                                    "instrument": instrument,
                                },
                            ).to_dict()
                        )
        return result

    def quotes(self, symbols: list[str]) -> list[dict]:
        quote_response = self.snapshot.get("quote") or {}
        data = quote_response.get("data") or {}
        rows = (
            (data.get("QuoteResponse") or {})
            .get("QuoteData", [])
        )
        if isinstance(rows, dict):
            rows = [rows]
        wanted = {symbol.upper() for symbol in symbols}
        result = []
        for item in rows or []:
            product = item.get("Product") or {}
            symbol = str(product.get("symbol") or "")
            if wanted and symbol.upper() not in wanted:
                continue
            detail = (
                item.get("All")
                or item.get("Intraday")
                or item.get("Fundamental")
                or item.get("MutualFund")
                or {}
            )
            result.append(
                UniversalQuote(
                    broker="ETRADE",
                    environment="SANDBOX",
                    symbol=symbol,
                    security_type=str(
                        product.get("securityType") or ""
                    ),
                    bid=_float(detail.get("bid")),
                    ask=_float(detail.get("ask")),
                    last=_float(
                        detail.get("lastTrade")
                    ),
                    open=_float(detail.get("open")),
                    high=_float(
                        detail.get("high")
                        or detail.get("high52")
                    ),
                    low=_float(
                        detail.get("low")
                        or detail.get("low52")
                    ),
                    previous_close=_float(
                        detail.get("previousClose")
                    ),
                    volume=_float(detail.get("volume")),
                    timestamp=str(
                        item.get("dateTime")
                        or item.get("dateTimeUTC")
                        or ""
                    ),
                    status=str(
                        item.get("quoteStatus") or ""
                    ),
                    raw=item,
                ).to_dict()
            )
        return result
