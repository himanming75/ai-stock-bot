from backtest.batch_recommendation_backtester import (
    print_batch_backtest_result,
    run_batch_recommendation_backtest,
    save_batch_backtest_result,
)
from config import SYMBOLS


def main() -> None:
    """
    V7.1 멀티 종목 추천 전략
    백테스트 테스트입니다.
    """

    print()
    print("=" * 88)
    print(
        "AI STOCK BOT V7.1 "
        "BATCH STRATEGY BACKTEST TEST"
    )
    print("=" * 88)

    try:
        result = run_batch_recommendation_backtest(
            symbols=SYMBOLS,

            period="10y",
            interval="1d",

            initial_cash=10_000.0,

            position_percent=20.0,

            entry_score=68.0,
            exit_score=42.0,

            stop_atr_multiple=1.5,
            target_atr_multiple=3.0,

            maximum_holding_days=20,

            commission_per_trade=0.0,
        )

        print_batch_backtest_result(
            result
        )

        (
            report_path,
            latest_path,
        ) = save_batch_backtest_result(
            result
        )

        print()
        print("=" * 88)
        print(
            "V7.1 BATCH BACKTEST "
            "TEST RESULT"
        )
        print("=" * 88)

        print(
            f"Total symbols       : "
            f"{result.total_symbols}"
        )

        print(
            f"Successful          : "
            f"{result.successful_count}"
        )

        print(
            f"Failed              : "
            f"{result.failed_count}"
        )

        print(
            f"Top symbol          : "
            f"{result.top_symbol or 'N/A'}"
        )

        if result.top_score is not None:
            print(
                f"Top score           : "
                f"{result.top_score:.2f}/100"
            )

        else:
            print(
                "Top score           : N/A"
            )

        print(
            f"Report file         : "
            f"{report_path}"
        )

        print(
            f"Latest file         : "
            f"{latest_path}"
        )

        print("=" * 88)

        print()
        print(
            "V7.1 batch recommendation "
            "backtester completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print(
            "사용자가 멀티 종목 "
            "백테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 88)
        print(
            "V7.1 BATCH BACKTEST ERROR"
        )
        print("=" * 88)

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