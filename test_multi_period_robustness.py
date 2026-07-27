from backtest.multi_period_robustness import (
    StrategyParameters,
    print_multi_period_result,
    run_multi_period_robustness_test,
    save_multi_period_result,
)


def main() -> None:
    """
    AI Stock Bot V7.6 Multi-Period Robustness Test.

    V7.4 Walk-Forward 검증에서 안정적으로 선택된 전략과
    V7.5 Parameter Robustness 검증에서 가장 높은 성과를 보인
    전략을 최근 1년, 2년, 3년, 5년 구간에서 비교합니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 118)
    print(
        "AI STOCK BOT V7.6 "
        "MULTI-PERIOD ROBUSTNESS TEST"
    )
    print("=" * 118)

    # ---------------------------------------------------------
    # 전략 1: 안정형 전략
    #
    # V7.4 Walk-Forward 테스트에서 여러 검증 구간에 걸쳐
    # 가장 자주 선택된 파라미터 조합입니다.
    # ---------------------------------------------------------
    stable_strategy = StrategyParameters(
        name="STABLE",

        entry_score=64.0,
        exit_score=42.0,

        stop_atr_multiple=1.50,
        target_atr_multiple=2.50,

        maximum_holding_days=20,
        position_percent=20.0,
    )

    # ---------------------------------------------------------
    # 전략 2: 공격형 후보 전략
    #
    # V7.5 Parameter Robustness 테스트에서
    # 가장 높은 개별 성과를 기록한 조합입니다.
    # ---------------------------------------------------------
    aggressive_strategy = StrategyParameters(
        name="AGGRESSIVE",

        entry_score=62.0,
        exit_score=44.0,

        stop_atr_multiple=1.50,
        target_atr_multiple=2.25,

        maximum_holding_days=20,
        position_percent=20.0,
    )

    strategies = [
        stable_strategy,
        aggressive_strategy,
    ]

    try:
        result = run_multi_period_robustness_test(
            symbol=symbol,

            strategies=strategies,

            # 최대 10년의 데이터를 내려받습니다.
            period="10y",
            interval="1d",

            # 동일한 종료일을 기준으로
            # 최근 1년, 2년, 3년, 5년을 검사합니다.
            periods_years=[
                1.0,
                2.0,
                3.0,
                5.0,
            ],

            # 미국 주식시장의 연간 거래일을
            # 약 252일로 계산합니다.
            estimated_trading_days_per_year=252,

            initial_cash=10_000.0,

            # 현재 테스트에서는 수수료를 0으로 설정합니다.
            # 이후 단계에서 거래 비용과 슬리피지를
            # 별도로 적용할 예정입니다.
            commission_per_trade=0.0,

            # 전략이 지나치게 적은 거래만 실행하고
            # 우연히 높은 결과를 내는 것을 방지합니다.
            #
            # 1년당 최소 8번을 기준으로 하므로:
            # 1년 = 8회
            # 2년 = 16회
            # 3년 = 24회
            # 5년 = 40회가 최소 기준입니다.
            minimum_trades_per_year=8,
        )

        # 전체 비교 결과를 터미널에 표시합니다.
        print_multi_period_result(
            result
        )

        # JSON 결과 파일을 저장합니다.
        (
            report_path,
            latest_path,
        ) = save_multi_period_result(
            result
        )

        print()
        print("=" * 118)
        print(
            "V7.6 MULTI-PERIOD ROBUSTNESS "
            "TEST RESULT"
        )
        print("=" * 118)

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

        print()
        print("TEST SUMMARY")
        print("-" * 118)

        print(
            f"Total strategies          : "
            f"{result.total_strategies}"
        )

        print(
            f"Total tests               : "
            f"{result.total_tests}"
        )

        print(
            f"Successful tests          : "
            f"{result.successful_tests}"
        )

        print(
            f"Failed tests              : "
            f"{result.failed_tests}"
        )

        print(
            "Test periods              : "
            + ", ".join(
                f"{period:g} year(s)"
                for period
                in result.requested_periods_years
            )
        )

        print()
        print("FINAL STRATEGY SELECTION")
        print("-" * 118)

        print(
            f"Winner strategy           : "
            f"{result.winner_strategy}"
        )

        print(
            f"Winner score              : "
            f"{result.winner_score:.2f}/100"
        )

        print(
            f"Runner-up strategy        : "
            f"{result.runner_up_strategy}"
        )

        print(
            f"Runner-up score           : "
            f"{result.runner_up_score:.2f}/100"
        )

        print(
            f"Score difference          : "
            f"{result.score_difference:+.2f}"
        )

        print()
        print("STRATEGY COMPARISON")
        print("-" * 118)

        for rank, summary in enumerate(
            result.strategy_summaries,
            start=1,
        ):
            parameters = summary[
                "parameters"
            ]

            print()
            print(
                f"Rank #{rank}: "
                f"{summary['strategy_name']}"
            )

            print(
                f"Overall score             : "
                f"{summary['overall_score']:.2f}/100"
            )

            print(
                f"Ranking status            : "
                f"{summary['ranking_status']}"
            )

            print(
                f"Entry score               : "
                f"{parameters['entry_score']:.0f}"
            )

            print(
                f"Exit score                : "
                f"{parameters['exit_score']:.0f}"
            )

            print(
                f"Stop ATR                  : "
                f"{parameters['stop_atr_multiple']:.2f}"
            )

            print(
                f"Target ATR                : "
                f"{parameters['target_atr_multiple']:.2f}"
            )

            print(
                f"Maximum holding days      : "
                f"{parameters['maximum_holding_days']}"
            )

            print(
                f"Position percent          : "
                f"{parameters['position_percent']:.2f}%"
            )

            print(
                f"Successful periods        : "
                f"{summary['successful_periods']}"
            )

            print(
                f"Failed periods            : "
                f"{summary['failed_periods']}"
            )

            print(
                f"Profitable periods        : "
                f"{summary['profitable_periods']}/"
                f"{summary['successful_periods']} "
                f"({summary['profitable_period_percent']:.2f}%)"
            )

            print(
                f"Acceptable periods        : "
                f"{summary['acceptable_periods']}/"
                f"{summary['successful_periods']} "
                f"({summary['acceptable_period_percent']:.2f}%)"
            )

            print(
                f"Average return            : "
                f"{summary['average_return_percent']:.2f}%"
            )

            print(
                f"Median return             : "
                f"{summary['median_return_percent']:.2f}%"
            )

            print(
                f"Average excess return     : "
                f"{summary['average_excess_return_percent']:+.2f}%p"
            )

            print(
                f"Average Sharpe            : "
                f"{summary['average_sharpe_ratio']:.2f}"
            )

            print(
                f"Median Sharpe             : "
                f"{summary['median_sharpe_ratio']:.2f}"
            )

            print(
                f"Average drawdown          : "
                f"{summary['average_drawdown_percent']:.2f}%"
            )

            print(
                f"Worst drawdown            : "
                f"{summary['worst_drawdown_percent']:.2f}%"
            )

            print(
                f"Average profit factor     : "
                f"{summary['average_profit_factor']:.2f}"
            )

            print(
                f"Average win rate          : "
                f"{summary['average_win_rate_percent']:.2f}%"
            )

            print(
                f"Total trades              : "
                f"{summary['total_trades']}"
            )

            print(
                f"Average period score      : "
                f"{summary['average_period_score']:.2f}/100"
            )

            print(
                f"Minimum period score      : "
                f"{summary['minimum_period_score']:.2f}/100"
            )

            print(
                f"Return consistency        : "
                f"{summary['return_consistency_score']:.2f}/100"
            )

            print(
                f"Sharpe consistency        : "
                f"{summary['sharpe_consistency_score']:.2f}/100"
            )

        print()
        print("FILES")
        print("-" * 118)

        print(
            f"Report file               : "
            f"{report_path}"
        )

        print(
            f"Latest file               : "
            f"{latest_path}"
        )

        print("=" * 118)

        print()
        print(
            "V7.6 multi-period robustness test "
            "completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 118)
        print("TEST CANCELLED")
        print("=" * 118)

        print(
            "사용자가 다중 기간 강건성 테스트를 "
            "중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 118)
        print(
            "V7.6 MULTI-PERIOD ROBUSTNESS ERROR"
        )
        print("=" * 118)

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