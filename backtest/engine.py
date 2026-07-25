def run_backtest(data, starting_cash=10000, fee_rate=0.001):
    cash = starting_cash
    shares = 0.0
    buy_price = None

    trades = []
    equity_curve = []

    for date, row in data.iterrows():
        signal = row["Signal"]
        close_price = row["Close"]

        if signal == "BUY" and shares == 0:
            buy_fee = cash * fee_rate
            investable_cash = cash - buy_fee

            shares = investable_cash / close_price
            buy_price = close_price
            cash = 0

            trades.append(
                {
                    "date": date,
                    "action": "BUY",
                    "price": close_price,
                    "fee": buy_fee,
                }
            )

        elif signal == "SELL" and shares > 0:
            gross_value = shares * close_price
            sell_fee = gross_value * fee_rate
            cash = gross_value - sell_fee

            profit_percent = ((close_price / buy_price) - 1) * 100

            trades.append(
                {
                    "date": date,
                    "action": "SELL",
                    "price": close_price,
                    "fee": sell_fee,
                    "profit_percent": profit_percent,
                }
            )

            shares = 0.0
            buy_price = None

        current_value = cash + shares * close_price
        equity_curve.append(current_value)

    final_close = data.iloc[-1]["Close"]
    final_value = cash + shares * final_close
    total_return = ((final_value / starting_cash) - 1) * 100

    completed_trades = [
        trade for trade in trades
        if trade["action"] == "SELL"
    ]

    winning_trades = [
        trade for trade in completed_trades
        if trade["profit_percent"] > 0
    ]

    losing_trades = [
        trade for trade in completed_trades
        if trade["profit_percent"] <= 0
    ]

    if completed_trades:
        win_rate = len(winning_trades) / len(completed_trades) * 100
    else:
        win_rate = 0.0

    peak = equity_curve[0]
    max_drawdown = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value

        drawdown = ((value / peak) - 1) * 100

        if drawdown < max_drawdown:
            max_drawdown = drawdown

    return {
        "starting_cash": starting_cash,
        "final_value": final_value,
        "total_return": total_return,
        "trades": trades,
        "completed_trades": len(completed_trades),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
    }