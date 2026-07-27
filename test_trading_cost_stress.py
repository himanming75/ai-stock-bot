from backtest.trading_cost_stress import (
    print_trading_cost_stress_result,
    run_trading_cost_stress_test,
    save_trading_cost_stress_result,
)


def main() -> None:
    """
    AI Stock Bot V7.7 Trading Cost Stress Test.

    V7.6에서 선택된 AGGRESSIVE 전략에
    여러 수수료와 슬리피지 조건을 적용해
    비용 반영 후에도 성과가 유지되는지 검사합니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 118)
    print(
        "AI STOCK BOT V7.7 "
        "TRADING COST STRESS TEST"
    )
    print("=" * 118)

    try:
        result = run_trading_cost_stress_test(
            symbol=symbol,

            # 최대 10년의 일봉 데이터를 사용합니다.
            period="10y",
            interval="1d",

            initial_cash=10_000.0,

            # -------------------------------------------------
            # V7.6 Multi-Period 테스트 우승 전략
            # -------------------------------------------------
            entry_score=62.0,
            exit_score=44.0,

            stop_atr_multiple=1.50,
            target_atr_multiple=2.25,

            maximum_holding_days=20,
            position_percent=20.0,

            # -------------------------------------------------
            # 주문 1회당 수수료 조건
            #
            # 매수 주문과 매도 주문에 각각 적용됩니다.
            # -------------------------------------------------
            commission_values=[
                0.0,
                1.0,
                2.0,
            ],

            # -------------------------------------------------
            # 주문 1회당 예상 슬리피지
            #
            # 0.05는 0.05%를 의미합니다.
            # 매수와 매도 양쪽 주문에 적용됩니다.
            # -------------------------------------------------
            slippage_percent_values=[
                0.00,
                0.05,
                0.10,
                0.20,
            ],

            # 비용 반영 후 최소 품질 기준입니다.
            minimum_net_sharpe=0.40,
            minimum_net_profit_factor=1.05,
            maximum_drawdown_limit=18.0,
        )

        # 전체 결과를 터미널에 출력합니다.
        print_trading_cost_stress_result(
            result
        )

        # JSON 결과를 저장합니다.
        (
            report_path,
            latest_path,
        ) = save_trading_cost_stress_result(
            result
        )

        print()
        print("=" * 118)
        print(
            "V7.7 TRADING COST STRESS "
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

        print(
            f"Cost robustness score     : "
            f"{result.cost_robustness_score:.2f}/100"
        )

        print()
        print("BASELINE PERFORMANCE")
        print("-" * 118)

        print(
            f"Gross return              : "
            f"{result.baseline_return_percent:.2f}%"
        )

        print(
            f"Gross Sharpe              : "
            f"{result.baseline_sharpe_ratio:.2f}"
        )

        print(
            f"Gross drawdown            : "
            f"{result.baseline_drawdown_percent:.2f}%"
        )

        print(
            f"Gross profit factor       : "
            f"{result.baseline_profit_factor:.2f}"
        )

        print(
            f"Completed trades          : "
            f"{result.baseline_total_trades}"
        )

        print()
        print("SCENARIO SUMMARY")
        print("-" * 118)

        print(
            f"Total scenarios           : "
            f"{result.total_scenarios}"
        )

        print(
            f"Successful scenarios      : "
            f"{result.successful_scenarios}"
        )

        print(
            f"Failed scenarios          : "
            f"{result.failed_scenarios}"
        )

        print(
            f"Profitable scenarios      : "
            f"{result.profitable_scenarios}/"
            f"{result.successful_scenarios} "
            f"({result.profitable_percent:.2f}%)"
        )

        print(
            f"Acceptable scenarios      : "
            f"{result.acceptable_scenarios}/"
            f"{result.successful_scenarios} "
            f"({result.acceptable_percent:.2f}%)"
        )

        print()
        print("NET PERFORMANCE")
        print("-" * 118)

        print(
            f"Average net return        : "
            f"{result.average_net_return_percent:.2f}%"
        )

        print(
            f"Worst net return          : "
            f"{result.worst_net_return_percent:.2f}%"
        )

        print(
            f"Average net Sharpe        : "
            f"{result.average_net_sharpe_ratio:.2f}"
        )

        print(
            f"Worst net Sharpe          : "
            f"{result.worst_net_sharpe_ratio:.2f}"
        )

        print(
            f"Average net drawdown      : "
            f"{result.average_net_drawdown_percent:.2f}%"
        )

        print(
            f"Worst net drawdown        : "
            f"{result.worst_net_drawdown_percent:.2f}%"
        )

        print()
        print("ESTIMATED TRADING COSTS")
        print("-" * 118)

        print(
            f"Average total cost        : "
            f"${result.average_total_cost:,.2f}"
        )

        print(
            f"Maximum total cost        : "
            f"${result.maximum_total_cost:,.2f}"
        )

        print(
            f"Average return reduction  : "
            f"{result.average_return_reduction_percent:.2f}%p"
        )

        print(
            f"Maximum return reduction  : "
            f"{result.maximum_return_reduction_percent:.2f}%p"
        )

        # ---------------------------------------------
        # 가장 높은 비용에서도 수익을 유지한 조건
        # ---------------------------------------------
        if result.break_even_scenario is not None:
            break_even = result.break_even_scenario

            print()
            print("HIGHEST SURVIVING COST SCENARIO")
            print("-" * 118)

            print(
                f"Commission per order      : "
                f"${break_even['commission_per_order']:.2f}"
            )

            print(
                f"Slippage per order        : "
                f"{break_even['slippage_percent_per_order']:.2f}%"
            )

            print(
                f"Estimated total cost      : "
                f"${break_even['estimated_total_cost']:,.2f}"
            )

            print(
                f"Total cost percent        : "
                f"{break_even['total_cost_percent']:.2f}%"
            )

            print(
                f"Net return                : "
                f"{break_even['net_return_percent']:.2f}%"
            )

            print(
                f"Estimated net Sharpe      : "
                f"{break_even['estimated_net_sharpe_ratio']:.2f}"
            )

            print(
                f"Estimated net PF          : "
                f"{break_even['estimated_net_profit_factor']:.2f}"
            )

            print(
                f"Scenario status           : "
                f"{break_even['status']}"
            )

        # ---------------------------------------------
        # 전체 조건 중 가장 나쁜 결과
        # ---------------------------------------------
        if result.worst_scenario is not None:
            worst = result.worst_scenario

            print()
            print("WORST SCENARIO")
            print("-" * 118)

            print(
                f"Commission per order      : "
                f"${worst['commission_per_order']:.2f}"
            )

            print(
                f"Slippage per order        : "
                f"{worst['slippage_percent_per_order']:.2f}%"
            )

            print(
                f"Estimated total cost      : "
                f"${worst['estimated_total_cost']:,.2f}"
            )

            print(
                f"Total cost percent        : "
                f"{worst['total_cost_percent']:.2f}%"
            )

            print(
                f"Net return                : "
                f"{worst['net_return_percent']:.2f}%"
            )

            print(
                f"Return reduction          : "
                f"{worst['return_reduction_percent']:.2f}%p"
            )

            print(
                f"Estimated net Sharpe      : "
                f"{worst['estimated_net_sharpe_ratio']:.2f}"
            )

            print(
                f"Estimated net drawdown    : "
                f"{worst['estimated_net_drawdown_percent']:.2f}%"
            )

            print(
                f"Estimated net PF          : "
                f"{worst['estimated_net_profit_factor']:.2f}"
            )

            print(
                f"Stress score              : "
                f"{worst['stress_score']:.2f}/100"
            )

            print(
                f"Scenario status           : "
                f"{worst['status']}"
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
            "V7.7 trading cost stress test "
            "completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 118)
        print("TEST CANCELLED")
        print("=" * 118)

        print(
            "사용자가 거래 비용 스트레스 테스트를 "
            "중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 118)
        print(
            "V7.7 TRADING COST STRESS ERROR"
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