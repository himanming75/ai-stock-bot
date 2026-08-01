from __future__ import annotations

from decimal import Decimal

from portfolio_engine import PortfolioSnapshot

from .models import BrokerAccount, BrokerPosition, ReconciliationSummary


class BrokerPortfolioReconciler:
    def reconcile(
        self,
        *,
        internal: PortfolioSnapshot,
        account: BrokerAccount,
        positions: tuple[BrokerPosition, ...],
        tolerance: Decimal = Decimal("0.01"),
    ) -> ReconciliationSummary:
        internal_positions = {p.symbol: p for p in internal.positions}
        broker_positions = {p.symbol: p for p in positions}

        missing_internal = tuple(sorted(set(broker_positions) - set(internal_positions)))
        missing_broker = tuple(sorted(set(internal_positions) - set(broker_positions)))
        mismatches: dict[str, dict[str, str]] = {}

        for symbol in sorted(set(internal_positions) & set(broker_positions)):
            internal_qty = internal_positions[symbol].quantity
            broker_qty = broker_positions[symbol].quantity
            if abs(internal_qty - broker_qty) > tolerance:
                mismatches[symbol] = {
                    "internal_quantity": str(internal_qty),
                    "broker_quantity": str(broker_qty),
                }

        cash_difference = account.cash - internal.cash
        equity_difference = account.equity - internal.equity
        matched = (
            abs(cash_difference) <= tolerance
            and abs(equity_difference) <= tolerance
            and not missing_internal
            and not missing_broker
            and not mismatches
        )
        return ReconciliationSummary(
            matched=matched,
            cash_difference=cash_difference,
            equity_difference=equity_difference,
            missing_internal_symbols=missing_internal,
            missing_broker_symbols=missing_broker,
            quantity_mismatches=mismatches,
        )
