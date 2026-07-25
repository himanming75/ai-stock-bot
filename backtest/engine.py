import pandas as pd


def run_backtest(
    data: pd.DataFrame,
    starting_cash: float = 10000.0,
) -> dict:
    """
    Signal 컬럼의 BUY/SELL 신호를 사용해 단순 백테스트를 실행합니다.

    매매 방식:
    - BUY 신호가 나오면 사용 가능한 현금으로 최대 수량 매수
    - 보유 중에는 추가 매수하지 않음
    - SELL 신호가 나오면 보유 주식 전량 매도
    - 마지막 날까지 주식을 보유하면 마지막 종가로 평가
    """

    required_columns = {"Close", "Signal"}

    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise ValueError(
            "백테스트에 필요한 컬럼이 없습니다: "
            + ", ".join(sorted(missing_columns))
        )

    if data.empty:
        raise ValueError("백테스트할 데이터가 없습니다.")

    if starting_cash <= 0:
        raise ValueError("starting_cash는 0보다 커야 합니다.")

    cash = float(starting_cash)
    shares = 0

    buy_price = None
    buy_date = None

    trades = []
    completed_trade_results = []
    equity_history = []

    for date, row in data.iterrows():
        close_price = float(row["Close"])
        signal = str(row["Signal"]).upper().strip()

        # BUY: 현재 주식을 보유하지 않을 때만 매수
        if signal == "BUY" and shares == 0:
            purchasable_shares = int(cash // close_price)

            if purchasable_shares > 0:
                shares = purchasable_shares
                cash -= shares * close_price

                buy_price = close_price
                buy_date = date

                trades.append(
                    {
                        "date": format_date(date),
                        "action": "BUY",
                        "price": close_price,
                        "shares": shares,
                        "cash_after": cash,
                    }
                )

        # SELL: 주식을 보유하고 있을 때만 매도
        elif signal == "SELL" and shares > 0:
            sale_value = shares * close_price
            cash += sale_value

            trade_profit = (
                (close_price - buy_price) * shares
                if buy_price is not None
                else 0.0
            )

            trade_return = (
                ((close_price / buy_price) - 1) * 100
                if buy_price
                else 0.0
            )

            trades.append(
                {
                    "date": format_date(date),
                    "action": "SELL",
                    "price": close_price,
                    "shares": shares,
                    "cash_after": cash,
                    "profit": trade_profit,
                    "return_percent": trade_return,
                }
            )

            completed_trade_results.append(
                {
                    "buy_date": format_date(buy_date),
                    "sell_date": format_date(date),
                    "buy_price": buy_price,
                    "sell_price": close_price,
                    "shares": shares,
                    "profit": trade_profit,
                    "return_percent": trade_return,
                }
            )

            shares = 0
            buy_price = None
            buy_date = None

        # 해당 날짜의 총 자산
        equity_value = cash + (shares * close_price)

        equity_history.append(
            {
                "date": date,
                "equity": equity_value,
            }
        )

    final_close = float(data.iloc[-1]["Close"])
    final_value = cash + (shares * final_close)

    total_return = (
        (final_value / starting_cash) - 1
    ) * 100

    completed_trades = len(completed_trade_results)

    winning_trades = sum(
        1
        for trade in completed_trade_results
        if trade["profit"] > 0
    )

    losing_trades = sum(
        1
        for trade in completed_trade_results
        if trade["profit"] < 0
    )

    break_even_trades = sum(
        1
        for trade in completed_trade_results
        if trade["profit"] == 0
    )

    win_rate = (
        winning_trades / completed_trades * 100
        if completed_trades > 0
        else 0.0
    )

    average_profit = calculate_average(
        [
            trade["profit"]
            for trade in completed_trade_results
            if trade["profit"] > 0
        ]
    )

    average_loss = calculate_average(
        [
            trade["profit"]
            for trade in completed_trade_results
            if trade["profit"] < 0
        ]
    )

    gross_profit = sum(
        trade["profit"]
        for trade in completed_trade_results
        if trade["profit"] > 0
    )

    gross_loss = abs(
        sum(
            trade["profit"]
            for trade in completed_trade_results
            if trade["profit"] < 0
        )
    )

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    max_drawdown = calculate_max_drawdown(equity_history)

    equity_curve = pd.DataFrame(equity_history)

    if not equity_curve.empty:
        equity_curve.set_index("date", inplace=True)

    return {
        "starting_cash": float(starting_cash),
        "final_cash": cash,
        "final_value": final_value,
        "total_return": total_return,

        # 전체 주문 수: BUY와 SELL을 각각 한 번으로 계산
        "trade_count": len(trades),

        # 매수부터 매도까지 완료된 거래 묶음 수
        "completed_trades": completed_trades,

        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "break_even_trades": break_even_trades,
        "win_rate": win_rate,

        "average_profit": average_profit,
        "average_loss": average_loss,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,

        "open_position": shares > 0,
        "open_shares": shares,
        "open_buy_price": buy_price,

        "trades": trades,
        "completed_trade_results": completed_trade_results,
        "equity_curve": equity_curve,
    }


def calculate_average(values: list[float]) -> float:
    """
    숫자 목록의 평균을 계산합니다.
    값이 없으면 0을 반환합니다.
    """

    if not values:
        return 0.0

    return sum(values) / len(values)


def calculate_max_drawdown(equity_history: list[dict]) -> float:
    """
    전체 자산의 최고점 대비 최대 하락률을 계산합니다.

    반환 예:
    -24.08은 최고점에서 최대 24.08% 하락했다는 뜻입니다.
    """

    if not equity_history:
        return 0.0

    peak = float(equity_history[0]["equity"])
    max_drawdown = 0.0

    for record in equity_history:
        current_equity = float(record["equity"])

        if current_equity > peak:
            peak = current_equity

        if peak > 0:
            drawdown = (
                (current_equity - peak) / peak
            ) * 100

            if drawdown < max_drawdown:
                max_drawdown = drawdown

    return max_drawdown


def format_date(date) -> str:
    """
    pandas 날짜 또는 일반 값을 YYYY-MM-DD 형식의 문자열로 변환합니다.
    """

    if hasattr(date, "strftime"):
        return date.strftime("%Y-%m-%d")

    return str(date)