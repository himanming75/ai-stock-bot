from __future__ import annotations
from decimal import Decimal
from math import sqrt
from typing import Any


class PerformanceMetricsEngine:
    def calculate(
        self,
        *,
        trade_returns: list[Decimal],
        trade_pnls: list[Decimal],
        equity_curve: list[Decimal],
    ) -> dict[str, Any]:
        trade_count = len(trade_returns)
        wins = sum(1 for value in trade_pnls if value > 0)
        losses = sum(1 for value in trade_pnls if value < 0)
        gross_profit = sum(
            (value for value in trade_pnls if value > 0),
            Decimal("0"),
        )
        gross_loss = abs(sum(
            (value for value in trade_pnls if value < 0),
            Decimal("0"),
        ))
        win_rate = (
            Decimal(wins) / Decimal(trade_count)
            if trade_count else Decimal("0")
        )
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0 else (
                Decimal("999") if gross_profit > 0 else Decimal("0")
            )
        )
        average_return = (
            sum(trade_returns, Decimal("0")) / Decimal(trade_count)
            if trade_count else Decimal("0")
        )
        variance = Decimal("0")
        if trade_count > 1:
            variance = sum(
                (value - average_return) ** 2 for value in trade_returns
            ) / Decimal(trade_count - 1)
        sharpe = (
            average_return / Decimal(str(sqrt(float(variance))))
            if variance > 0 else Decimal("0")
        )

        peak = Decimal("0")
        maximum_drawdown = Decimal("0")
        drawdowns = []
        for equity in equity_curve:
            peak = max(peak, equity)
            drawdown = (
                (peak - equity) / peak if peak > 0 else Decimal("0")
            )
            maximum_drawdown = max(maximum_drawdown, drawdown)
            drawdowns.append(str(drawdown.quantize(Decimal("0.0001"))))

        expectancy = (
            (
                win_rate * (
                    gross_profit / Decimal(wins) if wins else Decimal("0")
                )
                - (Decimal("1") - win_rate) * (
                    gross_loss / Decimal(losses) if losses else Decimal("0")
                )
            )
            if trade_count else Decimal("0")
        )

        return {
            "trade_count": trade_count,
            "wins": wins,
            "losses": losses,
            "win_rate": str(win_rate.quantize(Decimal("0.0001"))),
            "profit_factor": str(profit_factor.quantize(Decimal("0.0001"))),
            "average_return": str(
                average_return.quantize(Decimal("0.000001"))
            ),
            "sharpe_ratio": str(sharpe.quantize(Decimal("0.0001"))),
            "maximum_drawdown": str(
                maximum_drawdown.quantize(Decimal("0.0001"))
            ),
            "expectancy": str(expectancy.quantize(Decimal("0.0001"))),
            "equity_curve": [str(value) for value in equity_curve],
            "drawdown_curve": drawdowns,
        }
