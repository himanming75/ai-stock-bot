from backtest.strategy_optimizer import (
    print_optimization_result,
    run_strategy_optimization,
    save_optimization_result,
)


def main() -> None:
    """
    V7.2 전략 파라미터 최적화 테스트입니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 92)
    print(
        "AI STOCK BOT V7.2 "
        "STRATEGY OPTIMIZER TEST"
    )
    print("=" * 92)

    try:
        result = run_strategy_optimization(
            symbol=symbol,

            period="10y",
            interval="1d",

            initial_cash=10_000.0,

            commission_per_trade=0.0,

            # 2 × 2 × 2 × 2 × 3 × 1
            # 총 48개 조합입니다.
            entry_scores=[
                64.0,
                68.0,
            ],

            exit_scores=[
                38.0,
                42.0,
            ],

            stop_atr_multiples=[
                1.25,
                1.5,
            ],

            target_atr_multiples=[
                2.5,
                3.0,
            ],

            maximum_holding_days_list=[
                10,
                20,
                30,
            ],

            position_percents=[
                20.0,
            ],

            minimum_trades=30,

            top_n=10,
        )

        print_optimization_result(
            result
        )

        (
            report_path,
            latest_path,
        ) = save_optimization_result(
            result
        )

        print()
        print("=" * 92)
        print(
            "V7.2 OPTIMIZER TEST RESULT"
        )
        print("=" * 92)

        print(
            f"Symbol              : "
            f"{result.symbol}"
        )

        print(
            f"Total trials        : "
            f"{result.total_trials}"
        )

        print(
            f"Successful trials   : "
            f"{result.successful_trials}"
        )

        print(
            f"Failed trials       : "
            f"{result.failed_trials}"
        )

        if result.best_trial:
            best = result.best_trial

            print(
                f"Best score          : "
                f"{best['optimization_score']:.2f}/100"
            )

            print(
                f"Best entry score    : "
                f"{best['entry_score']:.2f}"
            )

            print(
                f"Best exit score     : "
                f"{best['exit_score']:.2f}"
            )

            print(
                f"Best stop ATR       : "
                f"{best['stop_atr_multiple']:.2f}"
            )

            print(
                f"Best target ATR     : "
                f"{best['target_atr_multiple']:.2f}"
            )

            print(
                f"Best holding days   : "
                f"{best['maximum_holding_days']}"
            )

            print(
                f"Best return         : "
                f"{best['strategy_return_percent']:.2f}%"
            )

            print(
                f"Best drawdown       : "
                f"{best['maximum_drawdown_percent']:.2f}%"
            )

            print(
                f"Best Sharpe         : "
                f"{best['sharpe_ratio']:.2f}"
            )

        print(
            f"Report file         : "
            f"{report_path}"
        )

        print(
            f"Latest file         : "
            f"{latest_path}"
        )

        print("=" * 92)

        print()
        print(
            "V7.2 strategy optimizer "
            "test completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print(
            "사용자가 전략 최적화 테스트를 "
            "중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 92)
        print(
            "V7.2 STRATEGY OPTIMIZER ERROR"
        )
        print("=" * 92)

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