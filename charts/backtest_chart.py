from pathlib import Path

# 중요:
# pyplot을 import하기 전에 GUI를 사용하지 않는 백엔드를 지정해야 합니다.
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def plot_backtest(
    data: pd.DataFrame,
    trades: list[dict],
    symbol: str,
    show_chart: bool = False,
) -> str:
    """
    백테스트 차트를 PNG 파일로 저장합니다.

    AI Stock Bot V2의 여러 종목 스캔에서는
    GUI 차트 창을 열지 않고 파일만 저장합니다.
    """

    required_columns = {
        "Close",
        "MA5",
        "MA20",
        "BB_UPPER",
        "BB_LOWER",
    }

    missing_columns = (
        required_columns
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "차트 생성에 필요한 컬럼이 없습니다: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    if data.empty:
        raise ValueError(
            "차트로 표시할 데이터가 없습니다."
        )

    symbol = str(symbol).upper().strip()

    chart_data = data.copy()
    chart_data.index = pd.to_datetime(
        chart_data.index
    )

    buy_dates = []
    buy_prices = []

    sell_dates = []
    sell_prices = []

    for trade in trades:
        action = (
            str(
                trade.get(
                    "action",
                    "",
                )
            )
            .upper()
            .strip()
        )

        trade_date = pd.to_datetime(
            trade.get("date")
        )

        trade_price = float(
            trade.get(
                "price",
                0,
            )
        )

        if action == "BUY":
            buy_dates.append(
                trade_date
            )

            buy_prices.append(
                trade_price
            )

        elif action == "SELL":
            sell_dates.append(
                trade_date
            )

            sell_prices.append(
                trade_price
            )

    # pyplot 전역 상태 대신 개별 Figure 객체를 만듭니다.
    figure, axis = plt.subplots(
        figsize=(16, 9)
    )

    axis.plot(
        chart_data.index,
        chart_data["Close"],
        label="Close",
        linewidth=1.2,
    )

    axis.plot(
        chart_data.index,
        chart_data["MA5"],
        label="MA5",
        linewidth=1.0,
    )

    axis.plot(
        chart_data.index,
        chart_data["MA20"],
        label="MA20",
        linewidth=1.0,
    )

    axis.plot(
        chart_data.index,
        chart_data["BB_UPPER"],
        label="BB Upper",
        linewidth=0.8,
        linestyle="--",
        alpha=0.7,
    )

    axis.plot(
        chart_data.index,
        chart_data["BB_LOWER"],
        label="BB Lower",
        linewidth=0.8,
        linestyle="--",
        alpha=0.7,
    )

    axis.fill_between(
        chart_data.index,
        chart_data["BB_LOWER"],
        chart_data["BB_UPPER"],
        alpha=0.08,
    )

    if buy_dates:
        axis.scatter(
            buy_dates,
            buy_prices,
            marker="^",
            s=80,
            label="BUY",
            zorder=5,
        )

    if sell_dates:
        axis.scatter(
            sell_dates,
            sell_prices,
            marker="v",
            s=80,
            label="SELL",
            zorder=5,
        )

    axis.set_title(
        f"{symbol} Backtest Chart"
    )

    axis.set_xlabel("Date")
    axis.set_ylabel("Price ($)")
    axis.legend()
    axis.grid(alpha=0.25)

    figure.tight_layout()

    output_directory = Path(
        "output"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / f"{symbol}_backtest.png"
    )

    figure.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    # 반드시 해당 Figure를 직접 닫습니다.
    plt.close(figure)

    # 혹시 남은 Figure가 있으면 모두 정리합니다.
    plt.close("all")

    print(
        f"Chart saved: {output_path}"
    )

    return str(output_path)