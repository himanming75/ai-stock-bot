from backtest.parameter_robustness import (
    print_parameter_robustness_result,
    run_parameter_robustness_test,
    save_parameter_robustness_result,
)


def main() -> None:
    """
    AI Stock Bot V7.5 Parameter Robustness Test.

    Walk-Forward 검증에서 자주 선택된 중심 파라미터와
    그 주변 파라미터들의 성과를 비교합니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 108)
    print(
        "AI STOCK BOT V7.5 "
        "PARAMETER ROBUSTNESS TEST"
    )
    print("=" * 108)

    try:
        result = run_parameter_robustness_test(
            symbol=symbol,

            period="10y",
            interval="1d",

            # 전체 데이터의 앞 70%는 제외하고
            # 뒤 30% 검증 구간에서만 주변값을 비교합니다.
            training_ratio=0.70,

            initial_cash=10_000.0,
            commission_per_trade=0.0,

            # V7.4 Walk-Forward에서 가장 자주 선택된
            # 중심 파라미터입니다.
            center_entry_score=64.0,
            center_exit_score=42.0,

            center_stop_atr_multiple=1.50,
            center_target_atr_multiple=2.50,

            center_maximum_holding_days=20,
            center_position_percent=20.0,

            # 중심값 주변 진입 점수를 검사합니다.
            entry_scores=[
                62.0,
                64.0,
                66.0,
            ],

            # 중심값 주변 청산 점수를 검사합니다.
            exit_scores=[
                40.0,
                42.0,
                44.0,
            ],

            # 이번 단계에서는 Stop ATR을 고정합니다.
            stop_atr_multiples=[
                1.50,
            ],

            # 중심값 주변 목표 ATR을 검사합니다.
            target_atr_multiples=[
                2.25,
                2.50,
                2.75,
            ],

            # 이번 단계에서는 보유 기간을 고정합니다.
            maximum_holding_days_list=[
                20,
            ],

            # 종목당 투자 비중도 고정합니다.
            position_percents=[
                20.0,
            ],

            minimum_validation_trades=10,

            # 주변 파라미터가 중심값 수익률의
            # 최소 70%를 유지해야 강건한 것으로 봅니다.
            robust_return_ratio=0.70,

            # 주변 파라미터가 중심값 Sharpe의
            # 최소 70%를 유지해야 합니다.
            robust_sharpe_ratio=0.70,
        )

        print_parameter_robustness_result(
            result
        )

        (
            report_path,
            latest_path,
        ) = save_parameter_robustness_result(
            result
        )

        print()
        print("=" * 108)
        print(
            "V7.5 PARAMETER ROBUSTNESS "
            "TEST RESULT"
        )
        print("=" * 108)

        print(
            f"Symbol                    : "
            f"{result.symbol}"
        )

        print(
            f"Validation status         : "
            f"{result.validation_status}"
        )

        print(
            f"Overfitting warning       : "
            f"{result.overfitting_warning}"
        )

        print(
            f"Robustness score          : "
            f"{result.parameter_robustness_score:.2f}/100"
        )

        print()
        print("TRIAL SUMMARY")
        print("-" * 108)

        print(
            f"Total trials              : "
            f"{result.total_trials}"
        )

        print(
            f"Successful trials         : "
            f"{result.successful_trials}"
        )

        print(
            f"Failed trials             : "
            f"{result.failed_trials}"
        )

        print(
            f"Profitable trials         : "
            f"{result.profitable_trials}/"
            f"{result.successful_trials} "
            f"({result.profitable_percent:.2f}%)"
        )

        print(
            f"Acceptable trials         : "
            f"{result.acceptable_trials}/"
            f"{result.successful_trials} "
            f"({result.acceptable_percent:.2f}%)"
        )

        print(
            f"Robust nearby trials      : "
            f"{result.robust_trial_percent:.2f}%"
        )

        print()
        print("PERFORMANCE SUMMARY")
        print("-" * 108)

        print(
            f"Average return            : "
            f"{result.average_return_percent:.2f}%"
        )

        print(
            f"Median return             : "
            f"{result.median_return_percent:.2f}%"
        )

        print(
            f"Average Sharpe            : "
            f"{result.average_sharpe_ratio:.2f}"
        )

        print(
            f"Median Sharpe             : "
            f"{result.median_sharpe_ratio:.2f}"
        )

        print(
            f"Average drawdown          : "
            f"{result.average_drawdown_percent:.2f}%"
        )

        print(
            f"Worst drawdown            : "
            f"{result.worst_drawdown_percent:.2f}%"
        )

        print(
            f"Average profit factor     : "
            f"{result.average_profit_factor:.2f}"
        )

        print(
            f"Average win rate          : "
            f"{result.average_win_rate_percent:.2f}%"
        )

        print()
        print("CENTER VS NEARBY")
        print("-" * 108)

        print(
            f"Center return             : "
            f"{result.center_return_percent:.2f}%"
        )

        print(
            f"Nearby average return     : "
            f"{result.nearby_average_return_percent:.2f}%"
        )

        print(
            f"Return difference         : "
            f"{result.center_vs_nearby_return_difference:+.2f}%p"
        )

        print(
            f"Center Sharpe             : "
            f"{result.center_sharpe_ratio:.2f}"
        )

        print(
            f"Nearby average Sharpe     : "
            f"{result.nearby_average_sharpe_ratio:.2f}"
        )

        print(
            f"Sharpe difference         : "
            f"{result.center_vs_nearby_sharpe_difference:+.2f}"
        )

        best_trial = result.best_trial

        if best_trial is not None:
            print()
            print("BEST TESTED PARAMETERS")
            print("-" * 108)

            print(
                f"Entry score               : "
                f"{best_trial['entry_score']:.0f}"
            )

            print(
                f"Exit score                : "
                f"{best_trial['exit_score']:.0f}"
            )

            print(
                f"Stop ATR                  : "
                f"{best_trial['stop_atr_multiple']:.2f}"
            )

            print(
                f"Target ATR                : "
                f"{best_trial['target_atr_multiple']:.2f}"
            )

            print(
                f"Maximum holding days      : "
                f"{best_trial['maximum_holding_days']}"
            )

            print(
                f"Strategy return           : "
                f"{best_trial['strategy_return_percent']:.2f}%"
            )

            print(
                f"Sharpe ratio              : "
                f"{best_trial['sharpe_ratio']:.2f}"
            )

            print(
                f"Maximum drawdown          : "
                f"{best_trial['maximum_drawdown_percent']:.2f}%"
            )

            print(
                f"Profit factor             : "
                f"{best_trial['profit_factor']:.2f}"
            )

            print(
                f"Total trades              : "
                f"{best_trial['total_trades']}"
            )

            print(
                f"Trial score               : "
                f"{best_trial['robustness_score']:.2f}/100"
            )

        print()
        print("FILES")
        print("-" * 108)

        print(
            f"Report file               : "
            f"{report_path}"
        )

        print(
            f"Latest file               : "
            f"{latest_path}"
        )

        print("=" * 108)

        print()
        print(
            "V7.5 parameter robustness test "
            "completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 108)
        print("TEST CANCELLED")
        print("=" * 108)

        print(
            "사용자가 파라미터 강건성 테스트를 "
            "중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 108)
        print(
            "V7.5 PARAMETER ROBUSTNESS ERROR"
        )
        print("=" * 108)

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