from __future__ import annotations
from collections import defaultdict
from decimal import Decimal

from .models import StrategyLearningSummary, TradeOutcome


D = Decimal


def _safe_div(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator if denominator != 0 else D("0")


def _max_drawdown(returns: list[Decimal]) -> Decimal:
    equity = D("1")
    peak = D("1")
    max_dd = D("0")

    for value in returns:
        equity *= D("1") + value
        if equity > peak:
            peak = equity
        drawdown = _safe_div(peak - equity, peak)
        if drawdown > max_dd:
            max_dd = drawdown

    return max_dd


def summarize_strategy(
    strategy_id: str,
    trades: list[TradeOutcome],
) -> StrategyLearningSummary:
    if not trades:
        return StrategyLearningSummary(
            strategy_id=strategy_id,
            trade_count=0,
            win_rate=D("0"),
            average_return=D("0"),
            average_win=D("0"),
            average_loss=D("0"),
            profit_factor=D("0"),
            sharpe_proxy=D("0"),
            max_drawdown=D("0"),
            stability=D("0"),
            status="INSUFFICIENT_DATA",
            weakness_reasons=("NO_TRADES",),
            recommendations=("COLLECT_MORE_EVIDENCE",),
        )

    returns = [item.pnl_ratio for item in trades]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]

    trade_count = len(returns)
    win_rate = D(str(len(wins))) / D(str(trade_count))
    average_return = sum(returns, D("0")) / D(str(trade_count))
    average_win = (
        sum(wins, D("0")) / D(str(len(wins)))
        if wins else D("0")
    )
    average_loss = (
        sum(losses, D("0")) / D(str(len(losses)))
        if losses else D("0")
    )
    gross_profit = sum(wins, D("0"))
    gross_loss = abs(sum(losses, D("0")))
    profit_factor = _safe_div(gross_profit, gross_loss)

    variance = (
        sum(
            (value - average_return) ** 2
            for value in returns
        )
        / D(str(trade_count))
    )
    volatility = variance.sqrt() if variance > 0 else D("0")
    sharpe_proxy = _safe_div(average_return, volatility)

    max_drawdown = _max_drawdown(returns)
    positive_consistency = D("1") - min(
        D("1"),
        abs(average_loss) * D("10"),
    )
    stability = max(
        D("0"),
        min(
            D("1"),
            win_rate * D("0.55")
            + positive_consistency * D("0.45"),
        ),
    )

    weaknesses = []
    recommendations = []

    if trade_count < 20:
        weaknesses.append("INSUFFICIENT_EVIDENCE")
        recommendations.append("COLLECT_MORE_TRADES")

    if win_rate < D("0.50"):
        weaknesses.append("LOW_WIN_RATE")
        recommendations.append("REVIEW_ENTRY_FILTER")

    if profit_factor < D("1.20"):
        weaknesses.append("LOW_PROFIT_FACTOR")
        recommendations.append("TIGHTEN_LOSS_CONTROL")

    if sharpe_proxy < D("0.20"):
        weaknesses.append("LOW_RISK_ADJUSTED_RETURN")
        recommendations.append("REDUCE_POSITION_SIZE")

    if max_drawdown > D("0.15"):
        weaknesses.append("HIGH_DRAWDOWN")
        recommendations.append("LOWER_RISK_BUDGET")

    if stability < D("0.55"):
        weaknesses.append("LOW_STABILITY")
        recommendations.append("REVIEW_REGIME_FILTER")

    if not weaknesses:
        status = "HEALTHY"
        recommendations.append("MAINTAIN_CURRENT_PARAMETERS")
    elif (
        "HIGH_DRAWDOWN" in weaknesses
        or "LOW_STABILITY" in weaknesses
    ):
        status = "WEAK"
    else:
        status = "WATCH"

    return StrategyLearningSummary(
        strategy_id=strategy_id,
        trade_count=trade_count,
        win_rate=win_rate,
        average_return=average_return,
        average_win=average_win,
        average_loss=average_loss,
        profit_factor=profit_factor,
        sharpe_proxy=sharpe_proxy,
        max_drawdown=max_drawdown,
        stability=stability,
        status=status,
        weakness_reasons=tuple(weaknesses),
        recommendations=tuple(dict.fromkeys(recommendations)),
    )


def summarize_all(
    trades: list[TradeOutcome],
) -> list[StrategyLearningSummary]:
    grouped = defaultdict(list)
    for trade in trades:
        grouped[trade.strategy_id].append(trade)

    return [
        summarize_strategy(strategy_id, grouped[strategy_id])
        for strategy_id in sorted(grouped)
    ]
