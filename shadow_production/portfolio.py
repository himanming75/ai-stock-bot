from __future__ import annotations
from decimal import Decimal
from typing import Any


class ShadowPortfolio:
    def __init__(self, starting_cash: Decimal) -> None:
        self.cash = starting_cash
        self.positions: dict[str, Decimal] = {}
        self.average_cost: dict[str, Decimal] = {}
        self.realized_pnl = Decimal("0")

    def apply_fill(self, fill: dict[str, Any]) -> dict[str, Any]:
        symbol = fill["symbol"]
        side = fill["side"]
        quantity = Decimal(str(fill["quantity"]))
        price = Decimal(str(fill["fill_price"]))
        notional = quantity * price

        if side == "buy":
            previous_qty = self.positions.get(symbol, Decimal("0"))
            previous_cost = self.average_cost.get(symbol, Decimal("0"))
            total_cost = previous_qty * previous_cost + notional
            new_qty = previous_qty + quantity
            self.positions[symbol] = new_qty
            self.average_cost[symbol] = (
                total_cost / new_qty if new_qty > 0 else Decimal("0")
            )
            self.cash -= notional
        elif side == "sell":
            available = self.positions.get(symbol, Decimal("0"))
            sell_qty = min(quantity, available)
            average_cost = self.average_cost.get(symbol, Decimal("0"))
            self.realized_pnl += sell_qty * (price - average_cost)
            self.positions[symbol] = available - sell_qty
            self.cash += sell_qty * price
            if self.positions[symbol] == 0:
                self.average_cost[symbol] = Decimal("0")
        else:
            raise ValueError("INVALID_SIDE")

        return self.snapshot()

    def snapshot(
        self,
        market_prices: dict[str, Decimal] | None = None,
    ) -> dict[str, Any]:
        market_prices = market_prices or {}
        position_rows = []
        market_value = Decimal("0")
        unrealized = Decimal("0")

        for symbol in sorted(self.positions):
            quantity = self.positions[symbol]
            if quantity == 0:
                continue
            average_cost = self.average_cost.get(symbol, Decimal("0"))
            price = market_prices.get(symbol, average_cost)
            value = quantity * price
            pnl = quantity * (price - average_cost)
            market_value += value
            unrealized += pnl
            position_rows.append({
                "symbol": symbol,
                "quantity": str(quantity.quantize(Decimal("0.000001"))),
                "average_cost": str(average_cost.quantize(Decimal("0.0001"))),
                "market_price": str(price.quantize(Decimal("0.0001"))),
                "market_value": str(value.quantize(Decimal("0.01"))),
                "unrealized_pnl": str(pnl.quantize(Decimal("0.01"))),
            })

        equity = self.cash + market_value
        return {
            "cash": str(self.cash.quantize(Decimal("0.01"))),
            "market_value": str(market_value.quantize(Decimal("0.01"))),
            "equity": str(equity.quantize(Decimal("0.01"))),
            "realized_pnl": str(self.realized_pnl.quantize(Decimal("0.01"))),
            "unrealized_pnl": str(unrealized.quantize(Decimal("0.01"))),
            "positions": position_rows,
            "actual_portfolio_modified": False,
        }


class ShadowRiskMetrics:
    def calculate(
        self,
        *,
        equity_curve: list[Decimal],
        returns: list[Decimal],
    ) -> dict[str, Any]:
        peak = Decimal("0")
        max_drawdown = Decimal("0")
        for equity in equity_curve:
            peak = max(peak, equity)
            drawdown = (
                (peak - equity) / peak if peak > 0 else Decimal("0")
            )
            max_drawdown = max(max_drawdown, drawdown)

        average_return = (
            sum(returns, Decimal("0")) / Decimal(len(returns))
            if returns else Decimal("0")
        )
        downside = [
            abs(value)
            for value in returns
            if value < 0
        ]
        downside_mean = (
            sum(downside, Decimal("0")) / Decimal(len(downside))
            if downside else Decimal("0")
        )
        return {
            "maximum_drawdown": str(
                max_drawdown.quantize(Decimal("0.0001"))
            ),
            "average_return": str(
                average_return.quantize(Decimal("0.000001"))
            ),
            "average_downside_return": str(
                downside_mean.quantize(Decimal("0.000001"))
            ),
            "risk_state": (
                "WARNING"
                if max_drawdown >= Decimal("0.10")
                else "OK"
            ),
            "actual_risk_action_performed": False,
        }
