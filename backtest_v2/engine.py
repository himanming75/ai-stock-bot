from __future__ import annotations

from typing import Any

from backtest_v2.broker import (
    apply_buy_fill,
    apply_sell_fill,
    commission_for,
)
from backtest_v2.models import Bar, Trade
from backtest_v2.statistics import (
    annualized_sharpe,
    annualized_sortino,
    max_drawdown,
    periodic_returns,
    trade_statistics,
)
from backtest_v2.strategy import crossover_signal


def run_backtest(
    symbol: str,
    bars: list[Bar],
    policy: dict[str, Any],
) -> dict[str, Any]:
    if not bars:
        raise ValueError("at least one bar is required")
    for bar in bars:
        bar.validate()

    initial_cash = float(policy.get("initial_cash", 100000.0))
    cash = initial_cash
    quantity = 0.0
    entry_price = 0.0
    entry_time = ""
    entry_commission = 0.0
    entry_slippage_cost = 0.0
    position_fraction = float(policy.get("position_fraction", 0.95))
    fast_period = int(policy.get("fast_period", 10))
    slow_period = int(policy.get("slow_period", 30))
    slippage_bps = float(policy.get("slippage_bps", 2.0))
    commission_bps = float(policy.get("commission_bps", 1.0))

    closes: list[float] = []
    trades: list[dict[str, Any]] = []
    equity_curve: list[float] = []
    daily_curve: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []

    for bar in bars:
        closes.append(bar.close)
        signal = crossover_signal(closes, fast_period, slow_period)
        signals.append({
            "timestamp": bar.timestamp,
            "signal": signal,
            "close": bar.close,
        })

        if signal == "BUY" and quantity == 0:
            fill_price, slippage_per_share = apply_buy_fill(
                bar.close,
                slippage_bps,
            )
            available = cash * position_fraction
            quantity = available / fill_price if fill_price > 0 else 0.0
            notional = quantity * fill_price
            entry_commission = commission_for(notional, commission_bps)
            cash -= notional + entry_commission
            entry_price = fill_price
            entry_time = bar.timestamp
            entry_slippage_cost = quantity * slippage_per_share

        elif signal == "SELL" and quantity > 0:
            exit_price, slippage_per_share = apply_sell_fill(
                bar.close,
                slippage_bps,
            )
            exit_notional = quantity * exit_price
            exit_commission = commission_for(exit_notional, commission_bps)
            gross_pnl = (exit_price - entry_price) * quantity
            total_commission = entry_commission + exit_commission
            total_slippage = (
                entry_slippage_cost + quantity * slippage_per_share
            )
            net_pnl = gross_pnl - total_commission
            return_pct = (
                net_pnl / (entry_price * quantity) * 100.0
                if entry_price and quantity
                else 0.0
            )
            cash += exit_notional - exit_commission
            trade = Trade(
                entry_time=entry_time,
                exit_time=bar.timestamp,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                side="LONG",
                gross_pnl=gross_pnl,
                commission=total_commission,
                slippage_cost=total_slippage,
                net_pnl=net_pnl,
                return_pct=return_pct,
            )
            trades.append(trade.to_dict())
            quantity = 0.0
            entry_price = 0.0
            entry_time = ""
            entry_commission = 0.0
            entry_slippage_cost = 0.0

        equity = cash + quantity * bar.close
        equity_curve.append(equity)
        daily_curve.append({
            "timestamp": bar.timestamp,
            "cash": round(cash, 4),
            "position_quantity": round(quantity, 8),
            "close": round(bar.close, 4),
            "equity": round(equity, 4),
        })

    if quantity > 0:
        last = bars[-1]
        exit_price, slippage_per_share = apply_sell_fill(
            last.close,
            slippage_bps,
        )
        exit_notional = quantity * exit_price
        exit_commission = commission_for(exit_notional, commission_bps)
        gross_pnl = (exit_price - entry_price) * quantity
        total_commission = entry_commission + exit_commission
        total_slippage = entry_slippage_cost + quantity * slippage_per_share
        net_pnl = gross_pnl - total_commission
        return_pct = (
            net_pnl / (entry_price * quantity) * 100.0
            if entry_price and quantity
            else 0.0
        )
        cash += exit_notional - exit_commission
        trades.append(Trade(
            entry_time=entry_time,
            exit_time=last.timestamp,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            side="LONG",
            gross_pnl=gross_pnl,
            commission=total_commission,
            slippage_cost=total_slippage,
            net_pnl=net_pnl,
            return_pct=return_pct,
        ).to_dict())
        quantity = 0.0
        equity_curve[-1] = cash
        daily_curve[-1]["cash"] = round(cash, 4)
        daily_curve[-1]["position_quantity"] = 0.0
        daily_curve[-1]["equity"] = round(cash, 4)

    ending_equity = equity_curve[-1]
    total_return_pct = (
        (ending_equity - initial_cash) / initial_cash * 100.0
        if initial_cash
        else 0.0
    )
    max_dd_pct, drawdown_curve = max_drawdown(equity_curve)
    returns = periodic_returns(equity_curve)
    trade_stats = trade_statistics(trades)
    sharpe = annualized_sharpe(returns)
    sortino = annualized_sortino(returns)
    calmar = total_return_pct / max_dd_pct if max_dd_pct > 0 else 0.0
    net_profit = ending_equity - initial_cash
    recovery_factor = net_profit / (initial_cash * max_dd_pct / 100.0) if max_dd_pct > 0 else 0.0

    return {
        "symbol": symbol.upper().strip() or "UNKNOWN",
        "initial_cash": round(initial_cash, 4),
        "ending_equity": round(ending_equity, 4),
        "net_profit": round(net_profit, 4),
        "total_return_pct": round(total_return_pct, 4),
        "maximum_drawdown_pct": round(max_dd_pct, 4),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "calmar_ratio": round(calmar, 4),
        "recovery_factor": round(recovery_factor, 4),
        "trade_statistics": trade_stats,
        "trades": trades,
        "signals": signals,
        "equity_curve": [round(value, 4) for value in equity_curve],
        "drawdown_curve_pct": [round(value, 4) for value in drawdown_curve],
        "daily_curve": daily_curve,
        "bar_count": len(bars),
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
