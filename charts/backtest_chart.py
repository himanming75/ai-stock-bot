from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_backtest(data: pd.DataFrame, trades: list, symbol: str) -> None:
    """가격, 이동평균선, 실제 매수·매도 거래를 차트로 표시합니다."""

    plt.figure(figsize=(14, 8))

    # 종가와 이동평균선
    plt.plot(data.index, data["Close"], label="Close", linewidth=1.5)
    plt.plot(data.index, data["MA5"], label="MA5", linewidth=1)
    plt.plot(data.index, data["MA20"], label="MA20", linewidth=1)

    # 백테스트 거래 기록 분리
    buy_trades = [trade for trade in trades if trade["action"] == "BUY"]
    sell_trades = [trade for trade in trades if trade["action"] == "SELL"]

    # BUY 지점
    if buy_trades:
        buy_dates = [trade["date"] for trade in buy_trades]
        buy_prices = [trade["price"] for trade in buy_trades]

        plt.scatter(
            buy_dates,
            buy_prices,
            marker="^",
            s=80,
            label="BUY",
            zorder=5,
        )

    # SELL 지점
    if sell_trades:
        sell_dates = [trade["date"] for trade in sell_trades]
        sell_prices = [trade["price"] for trade in sell_trades]

        plt.scatter(
            sell_dates,
            sell_prices,
            marker="v",
            s=80,
            label="SELL",
            zorder=5,
        )

    plt.title(f"{symbol} Backtest Chart")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    # output 폴더가 없으면 자동 생성
    output_directory = Path("output")
    output_directory.mkdir(exist_ok=True)

    output_file = output_directory / f"{symbol}_backtest.png"
    plt.savefig(output_file, dpi=150)

    print(f"Chart saved: {output_file}")

    plt.show()