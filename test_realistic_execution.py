from pathlib import Path
from typing import Any

from backtest.realistic_execution import (
    RealisticExecutionResult,
    print_realistic_execution_result,
    run_realistic_execution_backtest,
    save_realistic_execution_result,
)


def format_profit_factor(
    value: float,
) -> str:
    """
    Profit Factor를 출력하기 좋은 문자열로 변환합니다.

    손실 거래가 전혀 없으면 Profit Factor가
    무한대가 될 수 있으므로 INF로 표시합니다.
    """

    if value == float("inf"):
        return "INF"

    return f"{value:.2f}"


def print_scenario_header(
    scenario_number: int,
    total_scenarios: int,
    scenario_name: str,
    commission_per_order: float,
    slippage_percent: float,
) -> None:
    """
    각 체결 조건의 시작 정보를 출력합니다.
    """

    print()
    print("#" * 118)

    print(
        f"[{scenario_number}/{total_scenarios}] "
        f"{scenario_name}"
    )

    print(
        f"Commission per order     : "
        f"${commission_per_order:.2f}"
    )

    print(
        f"Slippage per order       : "
        f"{slippage_percent:.3f}%"
    )

    print("#" * 118)


def build_scenario_summary(
    scenario_name: str,
    commission_per_order: float,
    slippage_percent: float,
    result: RealisticExecutionResult,
    report_path: Path | None,
    latest_path: Path | None,
) -> dict[str, Any]:
    """
    한 시나리오의 핵심 결과를 사전으로 정리합니다.
    """

    return {
        "scenario_name": scenario_name,

        "commission_per_order": (
            commission_per_order
        ),

        "slippage_percent": (
            slippage_percent
        ),

        "success": result.success,

        "initial_cash": (
            result.initial_cash
        ),

        "final_value": (
            result.final_value
        ),

        "gross_baseline_return_percent": (
            result.gross_baseline_return_percent
        ),

        "net_return_percent": (
            result.net_return_percent
        ),

        "return_reduction_percent": (
            result.return_reduction_percent
        ),

        "buy_hold_return_percent": (
            result.buy_hold_return_percent
        ),

        "excess_return_percent": (
            result.excess_return_percent
        ),

        "maximum_drawdown_percent": (
            result.maximum_drawdown_percent
        ),

        "sharpe_ratio": (
            result.sharpe_ratio
        ),

        "profit_factor": (
            result.profit_factor
        ),

        "total_trades": (
            result.total_trades
        ),

        "win_rate_percent": (
            result.win_rate_percent
        ),

        "total_commission_cost": (
            result.total_commission_cost
        ),

        "total_slippage_cost": (
            result.total_slippage_cost
        ),

        "total_execution_cost": (
            result.total_execution_cost
        ),

        "execution_cost_percent": (
            result.execution_cost_percent_of_initial_cash
        ),

        "report_path": (
            str(report_path)
            if report_path is not None
            else None
        ),

        "latest_path": (
            str(latest_path)
            if latest_path is not None
            else None
        ),

        "error_type": (
            result.error_type
        ),

        "error_message": (
            result.error_message
        ),
    }


def print_comparison_table(
    scenario_summaries: list[
        dict[str, Any]
    ],
) -> None:
    """
    성공한 시나리오를 비교표로 출력합니다.
    """

    successful = [
        summary
        for summary in scenario_summaries
        if summary["success"]
    ]

    print()
    print("=" * 148)
    print(
        "AI STOCK BOT V7.8 "
        "REALISTIC EXECUTION COMPARISON"
    )
    print("=" * 148)

    if not successful:
        print(
            "성공적으로 완료된 시나리오가 없습니다."
        )

        print("=" * 148)
        return

    print(
        f"{'Rank':<6}"
        f"{'Scenario':<25}"
        f"{'Comm.':>9}"
        f"{'Slip.':>9}"
        f"{'Final Value':>15}"
        f"{'Net Return':>13}"
        f"{'Reduction':>12}"
        f"{'Sharpe':>9}"
        f"{'Drawdown':>12}"
        f"{'PF':>8}"
        f"{'Trades':>9}"
        f"{'Costs':>13}"
    )

    print("-" * 148)

    ranked = sorted(
        successful,
        key=lambda summary: (
            summary[
                "net_return_percent"
            ],

            summary[
                "sharpe_ratio"
            ],

            summary[
                "maximum_drawdown_percent"
            ],
        ),
        reverse=True,
    )

    for rank, summary in enumerate(
        ranked,
        start=1,
    ):
        profit_factor_text = (
            format_profit_factor(
                float(
                    summary[
                        "profit_factor"
                    ]
                )
            )
        )

        print(
            f"{rank:<6}"
            f"{summary['scenario_name']:<25}"
            f"${summary['commission_per_order']:>7.2f}"
            f"{summary['slippage_percent']:>8.3f}%"
            f"${summary['final_value']:>13,.2f}"
            f"{summary['net_return_percent']:>12.2f}%"
            f"{summary['return_reduction_percent']:>11.2f}%p"
            f"{summary['sharpe_ratio']:>9.2f}"
            f"{summary['maximum_drawdown_percent']:>11.2f}%"
            f"{profit_factor_text:>8}"
            f"{summary['total_trades']:>9}"
            f"${summary['total_execution_cost']:>11,.2f}"
        )

    print("=" * 148)


def main() -> None:
    """
    AI Stock Bot V7.8 Realistic Execution 테스트입니다.

    V7.6에서 선택된 AGGRESSIVE 전략을 유지하면서
    실제 매수·매도 체결가에 슬리피지를 적용하고
    주문마다 수수료를 현금에서 차감합니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 118)
    print(
        "AI STOCK BOT V7.8 "
        "REALISTIC EXECUTION TEST"
    )
    print("=" * 118)

    # ---------------------------------------------------------
    # 공통 전략 설정
    #
    # V7.6 Multi-Period Robustness 테스트에서 선택된
    # AGGRESSIVE 전략 파라미터입니다.
    # ---------------------------------------------------------
    common_settings = {
        "symbol": symbol,

        "period": "10y",
        "interval": "1d",

        "initial_cash": 10_000.0,
        "position_percent": 20.0,

        "entry_score": 62.0,
        "exit_score": 44.0,

        "stop_atr_multiple": 1.50,
        "target_atr_multiple": 2.25,

        "maximum_holding_days": 20,
    }

    # ---------------------------------------------------------
    # 현실적 체결 조건 비교
    # ---------------------------------------------------------
    scenarios = [
        {
            "name": "ZERO_COST",

            "commission_per_order": 0.0,
            "slippage_percent": 0.00,
        },

        {
            "name": "LOW_SLIPPAGE",

            "commission_per_order": 0.0,
            "slippage_percent": 0.05,
        },

        {
            "name": "STANDARD_COST",

            "commission_per_order": 1.0,
            "slippage_percent": 0.05,
        },

        {
            "name": "HIGH_COST",

            "commission_per_order": 2.0,
            "slippage_percent": 0.10,
        },
    ]

    scenario_summaries: list[
        dict[str, Any]
    ] = []

    total_scenarios = len(
        scenarios
    )

    try:
        for scenario_number, scenario in enumerate(
            scenarios,
            start=1,
        ):
            scenario_name = str(
                scenario["name"]
            )

            commission_per_order = float(
                scenario[
                    "commission_per_order"
                ]
            )

            slippage_percent = float(
                scenario[
                    "slippage_percent"
                ]
            )

            print_scenario_header(
                scenario_number=(
                    scenario_number
                ),

                total_scenarios=(
                    total_scenarios
                ),

                scenario_name=(
                    scenario_name
                ),

                commission_per_order=(
                    commission_per_order
                ),

                slippage_percent=(
                    slippage_percent
                ),
            )

            result = (
                run_realistic_execution_backtest(
                    **common_settings,

                    commission_per_order=(
                        commission_per_order
                    ),

                    slippage_percent=(
                        slippage_percent
                    ),
                )
            )

            print_realistic_execution_result(
                result
            )

            report_path: Path | None = None
            latest_path: Path | None = None

            if result.success:
                (
                    report_path,
                    latest_path,
                ) = save_realistic_execution_result(
                    result
                )

                print()
                print(
                    f"Scenario report          : "
                    f"{report_path}"
                )

                print(
                    f"Scenario latest          : "
                    f"{latest_path}"
                )

            else:
                print()
                print(
                    f"{scenario_name} failed: "
                    f"{result.error_type} - "
                    f"{result.error_message}"
                )

            scenario_summaries.append(
                build_scenario_summary(
                    scenario_name=(
                        scenario_name
                    ),

                    commission_per_order=(
                        commission_per_order
                    ),

                    slippage_percent=(
                        slippage_percent
                    ),

                    result=result,

                    report_path=(
                        report_path
                    ),

                    latest_path=(
                        latest_path
                    ),
                )
            )

        print_comparison_table(
            scenario_summaries
        )

        successful_scenarios = [
            summary
            for summary in scenario_summaries
            if summary["success"]
        ]

        failed_scenarios = [
            summary
            for summary in scenario_summaries
            if not summary["success"]
        ]

        successful_scenarios.sort(
            key=lambda summary: (
                summary[
                    "net_return_percent"
                ],

                summary[
                    "sharpe_ratio"
                ],
            ),
            reverse=True,
        )

        baseline = next(
            (
                summary
                for summary
                in successful_scenarios
                if summary[
                    "scenario_name"
                ] == "ZERO_COST"
            ),
            None,
        )

        highest_cost = next(
            (
                summary
                for summary
                in successful_scenarios
                if summary[
                    "scenario_name"
                ] == "HIGH_COST"
            ),
            None,
        )

        print()
        print("=" * 118)
        print(
            "V7.8 REALISTIC EXECUTION "
            "TEST RESULT"
        )
        print("=" * 118)

        print(
            f"Symbol                    : "
            f"{symbol}"
        )

        print(
            f"Total scenarios           : "
            f"{total_scenarios}"
        )

        print(
            f"Successful scenarios      : "
            f"{len(successful_scenarios)}"
        )

        print(
            f"Failed scenarios          : "
            f"{len(failed_scenarios)}"
        )

        if successful_scenarios:
            best = successful_scenarios[0]
            worst = successful_scenarios[-1]

            print()
            print("BEST REALISTIC RESULT")
            print("-" * 118)

            print(
                f"Scenario                  : "
                f"{best['scenario_name']}"
            )

            print(
                f"Commission per order      : "
                f"${best['commission_per_order']:.2f}"
            )

            print(
                f"Slippage per order        : "
                f"{best['slippage_percent']:.3f}%"
            )

            print(
                f"Final value               : "
                f"${best['final_value']:,.2f}"
            )

            print(
                f"Net return                : "
                f"{best['net_return_percent']:.2f}%"
            )

            print(
                f"Sharpe ratio              : "
                f"{best['sharpe_ratio']:.2f}"
            )

            print(
                f"Maximum drawdown          : "
                f"{best['maximum_drawdown_percent']:.2f}%"
            )

            print(
                f"Profit factor             : "
                f"{format_profit_factor(float(best['profit_factor']))}"
            )

            print()
            print("WORST REALISTIC RESULT")
            print("-" * 118)

            print(
                f"Scenario                  : "
                f"{worst['scenario_name']}"
            )

            print(
                f"Commission per order      : "
                f"${worst['commission_per_order']:.2f}"
            )

            print(
                f"Slippage per order        : "
                f"{worst['slippage_percent']:.3f}%"
            )

            print(
                f"Final value               : "
                f"${worst['final_value']:,.2f}"
            )

            print(
                f"Net return                : "
                f"{worst['net_return_percent']:.2f}%"
            )

            print(
                f"Sharpe ratio              : "
                f"{worst['sharpe_ratio']:.2f}"
            )

            print(
                f"Maximum drawdown          : "
                f"{worst['maximum_drawdown_percent']:.2f}%"
            )

            print(
                f"Profit factor             : "
                f"{format_profit_factor(float(worst['profit_factor']))}"
            )

        if (
            baseline is not None
            and highest_cost is not None
        ):
            realistic_return_loss = (
                float(
                    baseline[
                        "net_return_percent"
                    ]
                )
                - float(
                    highest_cost[
                        "net_return_percent"
                    ]
                )
            )

            final_value_loss = (
                float(
                    baseline[
                        "final_value"
                    ]
                )
                - float(
                    highest_cost[
                        "final_value"
                    ]
                )
            )

            print()
            print("ZERO COST VS HIGH COST")
            print("-" * 118)

            print(
                f"Zero-cost net return      : "
                f"{baseline['net_return_percent']:.2f}%"
            )

            print(
                f"High-cost net return      : "
                f"{highest_cost['net_return_percent']:.2f}%"
            )

            print(
                f"Return difference         : "
                f"{realistic_return_loss:.2f}%p"
            )

            print(
                f"Final value difference    : "
                f"${final_value_loss:,.2f}"
            )

            print(
                f"High-cost commissions     : "
                f"${highest_cost['total_commission_cost']:,.2f}"
            )

            print(
                f"High-cost slippage        : "
                f"${highest_cost['total_slippage_cost']:,.2f}"
            )

            print(
                f"High-cost execution cost  : "
                f"${highest_cost['total_execution_cost']:,.2f}"
            )

            print(
                f"High-cost drawdown        : "
                f"{highest_cost['maximum_drawdown_percent']:.2f}%"
            )

            # ---------------------------------------------
            # 간단한 생존 판정
            # ---------------------------------------------
            high_cost_survives = (
                float(
                    highest_cost[
                        "net_return_percent"
                    ]
                ) > 0.0
                and float(
                    highest_cost[
                        "sharpe_ratio"
                    ]
                ) >= 0.50
                and float(
                    highest_cost[
                        "profit_factor"
                    ]
                ) >= 1.10
                and abs(
                    float(
                        highest_cost[
                            "maximum_drawdown_percent"
                        ]
                    )
                ) <= 15.0
            )

            print()
            print("HIGH-COST SURVIVAL CHECK")
            print("-" * 118)

            print(
                f"Profitable                : "
                f"{highest_cost['net_return_percent'] > 0}"
            )

            print(
                f"Sharpe >= 0.50            : "
                f"{highest_cost['sharpe_ratio'] >= 0.50}"
            )

            print(
                f"Profit factor >= 1.10     : "
                f"{highest_cost['profit_factor'] >= 1.10}"
            )

            print(
                f"Drawdown within 15%       : "
                f"{abs(highest_cost['maximum_drawdown_percent']) <= 15.0}"
            )

            print(
                f"Overall survival          : "
                f"{high_cost_survives}"
            )

        if failed_scenarios:
            print()
            print("FAILED SCENARIOS")
            print("-" * 118)

            for failed in failed_scenarios:
                print(
                    f"- {failed['scenario_name']}: "
                    f"{failed['error_type']} - "
                    f"{failed['error_message']}"
                )

        print("=" * 118)

        print()
        print(
            "V7.8 realistic execution test "
            "completed successfully."
        )

        print(
            "주의: 과거 데이터 기반 체결 시뮬레이션이며 "
            "실제 주문 체결이나 미래 수익을 보장하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 118)
        print("TEST CANCELLED")
        print("=" * 118)

        print(
            "사용자가 현실적 체결 백테스트를 "
            "중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 118)
        print(
            "V7.8 REALISTIC EXECUTION ERROR"
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