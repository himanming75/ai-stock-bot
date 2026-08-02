from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence


class BrokerPortfolioStatus(str, Enum):
    MATCHED = "MATCHED"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class BrokerPositionState:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quantity": str(self.quantity),
            "average_entry_price": str(self.average_entry_price),
            "market_value": str(self.market_value),
            "unrealized_pnl": str(self.unrealized_pnl),
        }


@dataclass(frozen=True)
class PortfolioMismatch:
    code: str
    symbol: str | None
    expected: str
    actual: str
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrokerPortfolioReconciliationReport:
    status: BrokerPortfolioStatus
    safe_mode_engaged: bool
    autonomous_order_allowed: bool
    cash_matched: bool
    equity_matched: bool
    buying_power_matched: bool
    position_count_matched: bool
    position_symbols_matched: bool
    position_quantities_matched: bool
    average_prices_matched: bool
    market_values_matched: bool
    unrealized_pnl_matched: bool
    open_order_count_matched: bool
    reserved_buy_notional_matched: bool
    mismatch_count: int
    blocking_mismatch_count: int
    mismatches: tuple[PortfolioMismatch, ...]
    broker_positions: tuple[BrokerPositionState, ...]
    read_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "safe_mode_engaged": self.safe_mode_engaged,
            "autonomous_order_allowed": self.autonomous_order_allowed,
            "cash_matched": self.cash_matched,
            "equity_matched": self.equity_matched,
            "buying_power_matched": self.buying_power_matched,
            "position_count_matched": self.position_count_matched,
            "position_symbols_matched": self.position_symbols_matched,
            "position_quantities_matched": self.position_quantities_matched,
            "average_prices_matched": self.average_prices_matched,
            "market_values_matched": self.market_values_matched,
            "unrealized_pnl_matched": self.unrealized_pnl_matched,
            "open_order_count_matched": self.open_order_count_matched,
            "reserved_buy_notional_matched": self.reserved_buy_notional_matched,
            "mismatch_count": self.mismatch_count,
            "blocking_mismatch_count": self.blocking_mismatch_count,
            "mismatches": [item.to_json_dict() for item in self.mismatches],
            "broker_positions": [item.to_json_dict() for item in self.broker_positions],
            "read_requests_executed": self.read_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


@dataclass(frozen=True)
class BrokerPortfolioReconciliationPolicy:
    cash_tolerance: Decimal = Decimal("0.01")
    equity_tolerance: Decimal = Decimal("0.01")
    buying_power_tolerance: Decimal = Decimal("0.01")
    quantity_tolerance: Decimal = Decimal("0")
    average_price_tolerance: Decimal = Decimal("0.01")
    market_value_tolerance: Decimal = Decimal("0.05")
    unrealized_pnl_tolerance: Decimal = Decimal("0.05")
    reserved_notional_tolerance: Decimal = Decimal("0.05")

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if value < 0:
                raise ValueError(f"{name} cannot be negative")


class BrokerPortfolioReconciler:
    """Compares actual broker account/positions/orders with internal state."""

    def __init__(
        self,
        *,
        policy: BrokerPortfolioReconciliationPolicy | None = None,
    ) -> None:
        self.policy = policy or BrokerPortfolioReconciliationPolicy()
        self.policy.validate()

    def reconcile(
        self,
        *,
        broker_account: Mapping[str, Any],
        broker_positions: Sequence[Mapping[str, Any]],
        broker_open_orders: Sequence[Mapping[str, Any]],
        internal_portfolio: Mapping[str, Any],
        internal_open_orders: Sequence[Mapping[str, Any]],
    ) -> BrokerPortfolioReconciliationReport:
        mismatches: list[PortfolioMismatch] = []

        cash_matched = self._compare_money(
            code="CASH_MISMATCH",
            expected=_decimal(internal_portfolio.get("cash", "0")),
            actual=_decimal(broker_account.get("cash", "0")),
            tolerance=self.policy.cash_tolerance,
            detail="broker cash differs from internal cash",
            mismatches=mismatches,
        )
        equity_matched = self._compare_money(
            code="EQUITY_MISMATCH",
            expected=_decimal(internal_portfolio.get("equity", "0")),
            actual=_decimal(broker_account.get("equity", "0")),
            tolerance=self.policy.equity_tolerance,
            detail="broker equity differs from internal equity",
            mismatches=mismatches,
        )
        buying_power_matched = self._compare_money(
            code="BUYING_POWER_MISMATCH",
            expected=_decimal(internal_portfolio.get("buying_power", "0")),
            actual=_decimal(broker_account.get("buying_power", "0")),
            tolerance=self.policy.buying_power_tolerance,
            detail="broker buying power differs from internal buying power",
            mismatches=mismatches,
        )

        broker_states = tuple(
            sorted(
                (
                    BrokerPositionState(
                        symbol=str(item.get("symbol", "")).upper(),
                        quantity=_decimal(item.get("quantity", item.get("qty", "0"))),
                        average_entry_price=_decimal(
                            item.get("average_entry_price", item.get("average_price", "0"))
                        ),
                        market_value=_decimal(item.get("market_value", "0")),
                        unrealized_pnl=_decimal(item.get("unrealized_pnl", "0")),
                    )
                    for item in broker_positions
                ),
                key=lambda item: item.symbol,
            )
        )
        internal_positions = tuple(internal_portfolio.get("positions", ()))
        internal_by_symbol = {
            str(item.get("symbol", "")).upper(): item
            for item in internal_positions
            if str(item.get("symbol", "")).strip()
        }
        broker_by_symbol = {item.symbol: item for item in broker_states if item.symbol}

        position_count_matched = len(broker_states) == len(internal_positions)
        if not position_count_matched:
            mismatches.append(PortfolioMismatch(
                code="POSITION_COUNT_MISMATCH",
                symbol=None,
                expected=str(len(internal_positions)),
                actual=str(len(broker_states)),
                blocking=True,
                detail="broker and internal position counts differ",
            ))

        broker_symbols = tuple(sorted(broker_by_symbol))
        internal_symbols = tuple(sorted(internal_by_symbol))
        position_symbols_matched = broker_symbols == internal_symbols
        if not position_symbols_matched:
            mismatches.append(PortfolioMismatch(
                code="POSITION_SYMBOL_MISMATCH",
                symbol=None,
                expected=",".join(internal_symbols),
                actual=",".join(broker_symbols),
                blocking=True,
                detail="broker and internal held symbols differ",
            ))

        quantity_match = True
        average_match = True
        market_value_match = True
        unrealized_match = True
        for symbol in sorted(set(broker_symbols) | set(internal_symbols)):
            broker = broker_by_symbol.get(symbol)
            internal = internal_by_symbol.get(symbol)
            if broker is None or internal is None:
                quantity_match = False
                average_match = False
                market_value_match = False
                unrealized_match = False
                continue

            quantity_match &= self._compare_position(
                code="POSITION_QUANTITY_MISMATCH",
                symbol=symbol,
                expected=_decimal(internal.get("quantity", "0")),
                actual=broker.quantity,
                tolerance=self.policy.quantity_tolerance,
                detail="position quantity differs",
                mismatches=mismatches,
            )
            average_match &= self._compare_position(
                code="AVERAGE_PRICE_MISMATCH",
                symbol=symbol,
                expected=_decimal(
                    internal.get("average_entry_price", internal.get("average_price", "0"))
                ),
                actual=broker.average_entry_price,
                tolerance=self.policy.average_price_tolerance,
                detail="position average entry price differs",
                mismatches=mismatches,
            )
            market_value_match &= self._compare_position(
                code="MARKET_VALUE_MISMATCH",
                symbol=symbol,
                expected=_decimal(internal.get("market_value", "0")),
                actual=broker.market_value,
                tolerance=self.policy.market_value_tolerance,
                detail="position market value differs",
                mismatches=mismatches,
            )
            unrealized_match &= self._compare_position(
                code="UNREALIZED_PNL_MISMATCH",
                symbol=symbol,
                expected=_decimal(internal.get("unrealized_pnl", "0")),
                actual=broker.unrealized_pnl,
                tolerance=self.policy.unrealized_pnl_tolerance,
                detail="position unrealized P/L differs",
                mismatches=mismatches,
            )

        open_order_count_matched = len(broker_open_orders) == len(internal_open_orders)
        if not open_order_count_matched:
            mismatches.append(PortfolioMismatch(
                code="OPEN_ORDER_COUNT_MISMATCH",
                symbol=None,
                expected=str(len(internal_open_orders)),
                actual=str(len(broker_open_orders)),
                blocking=True,
                detail="broker and internal open-order counts differ",
            ))

        broker_reserved = _reserved_buy_notional(broker_open_orders)
        internal_reserved = _reserved_buy_notional(internal_open_orders)
        reserved_buy_notional_matched = (
            abs(broker_reserved - internal_reserved)
            <= self.policy.reserved_notional_tolerance
        )
        if not reserved_buy_notional_matched:
            mismatches.append(PortfolioMismatch(
                code="RESERVED_BUY_NOTIONAL_MISMATCH",
                symbol=None,
                expected=str(internal_reserved),
                actual=str(broker_reserved),
                blocking=True,
                detail="broker and internal reserved BUY notionals differ",
            ))

        blocking = sum(1 for item in mismatches if item.blocking)
        safe_mode = blocking > 0
        return BrokerPortfolioReconciliationReport(
            status=(
                BrokerPortfolioStatus.SAFE_MODE
                if safe_mode
                else BrokerPortfolioStatus.MATCHED
            ),
            safe_mode_engaged=safe_mode,
            autonomous_order_allowed=not safe_mode,
            cash_matched=cash_matched,
            equity_matched=equity_matched,
            buying_power_matched=buying_power_matched,
            position_count_matched=position_count_matched,
            position_symbols_matched=position_symbols_matched,
            position_quantities_matched=quantity_match,
            average_prices_matched=average_match,
            market_values_matched=market_value_match,
            unrealized_pnl_matched=unrealized_match,
            open_order_count_matched=open_order_count_matched,
            reserved_buy_notional_matched=reserved_buy_notional_matched,
            mismatch_count=len(mismatches),
            blocking_mismatch_count=blocking,
            mismatches=tuple(mismatches),
            broker_positions=broker_states,
            read_requests_executed=0,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )

    @staticmethod
    def _compare_money(
        *,
        code: str,
        expected: Decimal,
        actual: Decimal,
        tolerance: Decimal,
        detail: str,
        mismatches: list[PortfolioMismatch],
    ) -> bool:
        matched = abs(expected - actual) <= tolerance
        if not matched:
            mismatches.append(PortfolioMismatch(
                code=code,
                symbol=None,
                expected=str(expected),
                actual=str(actual),
                blocking=True,
                detail=detail,
            ))
        return matched

    @staticmethod
    def _compare_position(
        *,
        code: str,
        symbol: str,
        expected: Decimal,
        actual: Decimal,
        tolerance: Decimal,
        detail: str,
        mismatches: list[PortfolioMismatch],
    ) -> bool:
        matched = abs(expected - actual) <= tolerance
        if not matched:
            mismatches.append(PortfolioMismatch(
                code=code,
                symbol=symbol,
                expected=str(expected),
                actual=str(actual),
                blocking=True,
                detail=detail,
            ))
        return matched


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _reserved_buy_notional(orders: Sequence[Mapping[str, Any]]) -> Decimal:
    total = Decimal("0")
    for item in orders:
        if str(item.get("side", "")).upper() != "BUY":
            continue
        quantity = _decimal(item.get("quantity", item.get("qty", "0")))
        filled = _decimal(
            item.get("filled_quantity", item.get("filled_qty", "0"))
        )
        remaining = max(Decimal("0"), quantity - filled)
        price = _decimal(
            item.get(
                "limit_price",
                item.get("estimated_price", item.get("price", "0")),
            )
        )
        total += remaining * price
    return total
