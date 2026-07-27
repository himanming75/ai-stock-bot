from backtest.out_of_sample_validator import (
    print_out_of_sample_result,
    run_out_of_sample_validation,
    save_out_of_sample_result,
)


def main() -> None:
    """
    V7.3 Out-of-Sample 검증 테스트입니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 92)
    print(
        "AI STOCK BOT V7.3 "
        "OUT-OF-SAMPLE VALIDATOR TEST"
    )
    print("=" * 92)

    try:
        result = run_out_of_sample_validation(
            symbol=symbol,

            period="10y",
            interval="1d",

            # 앞쪽 70%는 훈련,
            # 뒤쪽 30%는 검증에 사용합니다.
            training_ratio=0.70,

            initial_cash=10_000.0,

            commission_per_trade=0.0,

            # V7.2와 동일한 48개 조합을
            # 훈련 구간에서만 시험합니다.
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
                1.50,
            ],

            target_atr_multiples=[
                2.50,
                3.00,
            ],

            maximum_holding_days_list=[
                10,
                20,
                30,
            ],

            position_percents=[
                20.0,
            ],

            minimum_training_trades=30,

            # 검증 구간에서 최소 10회 이상의
            # 거래가 있어야 표본이 충분하다고 봅니다.
            minimum_validation_trades=10,

            top_n=10,
        )

        print_out_of_sample_result(
            result
        )

        (
            report_path,
            latest_path,
        ) = save_out_of_sample_result(
            result
        )

        print()
        print("=" * 92)
        print(
            "V7.3 OUT-OF-SAMPLE "
            "TEST RESULT"
        )
        print("=" * 92)

        print(
            f"Symbol              : "
            f"{result.symbol}"
        )

        print(
            f"Validation status   : "
            f"{result.validation_status}"
        )

        print(
            f"Training return     : "
            f"{result.training_return_percent:.2f}%"
        )

        print(
            f"Validation return   : "
            f"{result.validation_return_percent:.2f}%"
        )

        print(
            f"Validation Sharpe   : "
            f"{result.validation_sharpe_ratio:.2f}"
        )

        print(
            f"Validation drawdown : "
            f"{result.validation_drawdown_percent:.2f}%"
        )

        print(
            f"Return retention    : "
            f"{result.return_retention_percent:.2f}%"
        )

        print(
            f"Overfit warning     : "
            f"{result.overfitting_warning}"
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
            "V7.3 out-of-sample validator "
            "completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 92)
        print("TEST CANCELLED")
        print("=" * 92)

        print(
            "사용자가 검증 테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 92)
        print(
            "V7.3 OUT-OF-SAMPLE ERROR"
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