from backtest.walk_forward_validator import (
    print_walk_forward_result,
    run_walk_forward_validation,
    save_walk_forward_result,
)


def main() -> None:
    """
    V7.4 Walk-Forward 검증 테스트입니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 104)
    print(
        "AI STOCK BOT V7.4 "
        "WALK-FORWARD VALIDATOR TEST"
    )
    print("=" * 104)

    try:
        result = run_walk_forward_validation(
            symbol=symbol,

            period="10y",
            interval="1d",

            # 과거 4년을 사용해 최적화한 뒤
            # 다음 1년을 검증합니다.
            training_years=4.0,
            validation_years=1.0,

            # 검증 후 1년씩 앞으로 이동합니다.
            step_years=1.0,

            estimated_trading_days_per_year=252,

            initial_cash=10_000.0,

            commission_per_trade=0.0,

            # 2 × 2 × 1 × 2 × 2 × 1
            # 구간당 총 16개 조합
            entry_scores=[
                64.0,
                68.0,
            ],

            exit_scores=[
                38.0,
                42.0,
            ],

            stop_atr_multiples=[
                1.50,
            ],

            target_atr_multiples=[
                2.50,
                3.00,
            ],

            maximum_holding_days_list=[
                10,
                20,
            ],

            position_percents=[
                20.0,
            ],

            minimum_training_trades=30,
            minimum_validation_trades=10,

            top_n=5,
        )

        print_walk_forward_result(
            result
        )

        (
            report_path,
            latest_path,
        ) = save_walk_forward_result(
            result
        )

        print()
        print("=" * 104)
        print(
            "V7.4 WALK-FORWARD "
            "TEST RESULT"
        )
        print("=" * 104)

        print(
            f"Symbol                   : "
            f"{result.symbol}"
        )

        print(
            f"Validation status        : "
            f"{result.validation_status}"
        )

        print(
            f"Total windows            : "
            f"{result.total_windows}"
        )

        print(
            f"Successful windows       : "
            f"{result.successful_windows}"
        )

        print(
            f"Profitable windows       : "
            f"{result.profitable_window_percent:.2f}%"
        )

        print(
            f"Acceptable windows       : "
            f"{result.acceptable_window_percent:.2f}%"
        )

        print(
            f"Beat default return      : "
            f"{result.beat_default_return_percent:.2f}%"
        )

        print(
            f"Average validation return: "
            f"{result.average_validation_return_percent:.2f}%"
        )

        print(
            f"Average default return   : "
            f"{result.average_default_return_percent:.2f}%"
        )

        print(
            f"Average validation Sharpe: "
            f"{result.average_validation_sharpe_ratio:.2f}"
        )

        print(
            f"Worst drawdown           : "
            f"{result.worst_validation_drawdown_percent:.2f}%"
        )

        print(
            f"Parameter stability      : "
            f"{result.parameter_stability_score:.2f}/100"
        )

        print(
            f"Overfitting warning      : "
            f"{result.overfitting_warning}"
        )

        print(
            f"Report file              : "
            f"{report_path}"
        )

        print(
            f"Latest file              : "
            f"{latest_path}"
        )

        print("=" * 104)

        print()
        print(
            "V7.4 walk-forward validator "
            "completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 104)
        print("TEST CANCELLED")
        print("=" * 104)

        print(
            "사용자가 Walk-Forward 테스트를 "
            "중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 104)
        print(
            "V7.4 WALK-FORWARD ERROR"
        )
        print("=" * 104)

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