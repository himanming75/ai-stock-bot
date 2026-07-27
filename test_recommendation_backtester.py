from backtest.recommendation_backtester import (
    print_backtest_result,
    run_recommendation_backtest,
    save_backtest_result,
)


def main() -> None:
    """
    V7.0 추천 전략 백테스트 테스트입니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 80)
    print(
        "AI STOCK BOT V7.0 "
        "RECOMMENDATION BACKTEST TEST"
    )
    print("=" * 80)

    try:
        result = run_recommendation_backtest(
            symbol=symbol,

            period="10y",
            interval="1d",

            initial_cash=10_000.0,

            # 한 번 진입할 때 현재 현금의
            # 최대 20%를 사용합니다.
            position_percent=20.0,

            # BUY 이상에서 진입
            entry_score=68.0,

            # HOLD 아래로 내려가면 청산
            exit_score=42.0,

            # ATR 기준 손절 및 목표가
            stop_atr_multiple=1.5,
            target_atr_multiple=3.0,

            # 최대 약 4주 보유
            maximum_holding_days=20,

            # 첫 테스트에서는 수수료를 0으로 설정
            commission_per_trade=0.0,
        )

        print_backtest_result(
            result
        )

        if not result.success:
            raise RuntimeError(
                result.error_message
                or "백테스트가 실패했습니다."
            )

        (
            report_path,
            latest_path,
        ) = save_backtest_result(
            result
        )

        print()
        print("=" * 80)
        print(
            "V7.0 BACKTEST TEST RESULT"
        )
        print("=" * 80)

        print(
            f"Symbol              : "
            f"{result.symbol}"
        )

        print(
            f"Strategy return     : "
            f"{result.total_return_percent:.2f}%"
        )

        print(
            f"Buy and hold return : "
            f"{result.buy_hold_return_percent:.2f}%"
        )

        print(
            f"Total trades        : "
            f"{result.total_trades}"
        )

        print(
            f"Win rate            : "
            f"{result.win_rate_percent:.2f}%"
        )

        print(
            f"Maximum drawdown    : "
            f"{result.maximum_drawdown_percent:.2f}%"
        )

        print(
            f"Sharpe ratio        : "
            f"{result.sharpe_ratio:.2f}"
        )

        print(
            f"Report file         : "
            f"{report_path}"
        )

        print(
            f"Latest file         : "
            f"{latest_path}"
        )

        print("=" * 80)

        print()
        print(
            "V7.0 recommendation backtester "
            "test completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print(
            "사용자가 백테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 80)
        print(
            "V7.0 BACKTEST TEST ERROR"
        )
        print("=" * 80)

        print(
            f"Error type   : "
            f"{type(error).__name__}"
        )

        print(
            f"Error message: "
            f"{error}"
        )


if __name__ == "__main__":
    main()