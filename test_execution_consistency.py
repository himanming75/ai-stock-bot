from pathlib import Path
from typing import Any

import numpy as np

from backtest.execution_consistency import (
    ExecutionConsistencyResult,
    print_execution_consistency_result,
    run_execution_consistency_validation,
    save_execution_consistency_result,
)


def format_profit_factor(
    value: float,
) -> str:
    """
    Profit Factor를 터미널에 표시할 문자열로 바꿉니다.

    손실 거래가 전혀 없으면 Profit Factor가
    무한대일 수 있으므로 INF로 표시합니다.
    """

    if np.isinf(value):
        return "INF"

    return f"{value:.2f}"


def print_test_header() -> None:
    """
    V7.9 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V7.9 "
        "EXECUTION CONSISTENCY VALIDATOR TEST"
    )
    print("=" * 140)


def print_test_summary(
    result: ExecutionConsistencyResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    테스트 완료 후 핵심 결과를 다시 요약합니다.
    """

    print()
    print("=" * 140)
    print(
        "V7.9 EXECUTION CONSISTENCY "
        "TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                       : "
        f"{result.symbol}"
    )

    print(
        f"Validation status            : "
        f"{result.validation_status}"
    )

    print(
        f"Consistency score            : "
        f"{result.consistency_score:.2f}/100"
    )

    print(
        f"Overfitting warning          : "
        f"{result.overfitting_warning}"
    )

    print()
    print("BASELINE")
    print("-" * 140)

    print(
        f"Baseline trades              : "
        f"{result.baseline_trade_count}"
    )

    print(
        f"Baseline final value         : "
        f"${result.baseline_final_value:,.2f}"
    )

    print(
        f"Baseline return              : "
        f"{result.baseline_return_percent:.2f}%"
    )

    print(
        f"Baseline Sharpe              : "
        f"{result.baseline_sharpe_ratio:.2f}"
    )

    print(
        f"Baseline drawdown            : "
        f"{result.baseline_drawdown_percent:.2f}%"
    )

    print(
        f"Baseline profit factor       : "
        f"{format_profit_factor(result.baseline_profit_factor)}"
    )

    print()
    print("TRADE PATH CONSISTENCY")
    print("-" * 140)

    print(
        f"Total scenarios              : "
        f"{result.total_scenarios}"
    )

    print(
        f"Successful scenarios         : "
        f"{result.successful_scenarios}"
    )

    print(
        f"Failed scenarios             : "
        f"{result.failed_scenarios}"
    )

    print(
        f"Matching trade paths         : "
        f"{result.matching_trade_paths}/"
        f"{result.successful_scenarios}"
    )

    print(
        f"Mismatched trade paths       : "
        f"{result.mismatched_trade_paths}"
    )

    print(
        f"Path consistency             : "
        f"{result.path_consistency_percent:.2f}%"
    )

    print()
    print("COST SURVIVAL")
    print("-" * 140)

    print(
        f"Profitable scenarios         : "
        f"{result.profitable_scenarios}/"
        f"{result.successful_scenarios} "
        f"({result.profitable_percent:.2f}%)"
    )

    print(
        f"Acceptable scenarios         : "
        f"{result.acceptable_scenarios}/"
        f"{result.successful_scenarios} "
        f"({result.acceptable_percent:.2f}%)"
    )

    print(
        f"Average net return           : "
        f"{result.average_net_return_percent:.2f}%"
    )

    print(
        f"Worst net return             : "
        f"{result.worst_net_return_percent:.2f}%"
    )

    print(
        f"Average Sharpe               : "
        f"{result.average_sharpe_ratio:.2f}"
    )

    print(
        f"Worst Sharpe                 : "
        f"{result.worst_sharpe_ratio:.2f}"
    )

    print(
        f"Average drawdown             : "
        f"{result.average_drawdown_percent:.2f}%"
    )

    print(
        f"Worst drawdown               : "
        f"{result.worst_drawdown_percent:.2f}%"
    )

    print()
    print("EXECUTION COSTS")
    print("-" * 140)

    print(
        f"Average execution cost       : "
        f"${result.average_execution_cost:,.2f}"
    )

    print(
        f"Maximum execution cost       : "
        f"${result.maximum_execution_cost:,.2f}"
    )

    print(
        f"Average return reduction     : "
        f"{result.average_return_reduction_percent:.2f}%p"
    )

    print(
        f"Maximum return reduction     : "
        f"{result.maximum_return_reduction_percent:.2f}%p"
    )

    print()
    print("SCENARIO DETAIL")
    print("-" * 140)

    print(
        f"{'No.':<5}"
        f"{'Scenario':<20}"
        f"{'Commission':>13}"
        f"{'Slippage':>12}"
        f"{'Trades':>9}"
        f"{'Path':>8}"
        f"{'Return':>11}"
        f"{'Reduction':>12}"
        f"{'Sharpe':>9}"
        f"{'Drawdown':>12}"
        f"{'PF':>8}"
        f"{'Cost':>13}"
        f"{'Status':>14}"
    )

    print("-" * 140)

    successful_scenarios = [
        scenario
        for scenario in result.scenarios
        if scenario["success"]
    ]

    successful_scenarios.sort(
        key=lambda scenario: int(
            scenario["scenario_number"]
        )
    )

    for scenario in successful_scenarios:
        profit_factor = float(
            scenario["profit_factor"]
        )

        print(
            f"{int(scenario['scenario_number']):<5}"
            f"{str(scenario['scenario_name']):<20}"
            f"${float(scenario['commission_per_order']):>11.2f}"
            f"{float(scenario['slippage_percent']):>11.3f}%"
            f"{int(scenario['total_trades']):>9}"
            f"{str(scenario['trade_path_match']):>8}"
            f"{float(scenario['net_return_percent']):>10.2f}%"
            f"{float(scenario['return_reduction_percent']):>11.2f}%p"
            f"{float(scenario['sharpe_ratio']):>9.2f}"
            f"{float(scenario['maximum_drawdown_percent']):>11.2f}%"
            f"{format_profit_factor(profit_factor):>8}"
            f"${float(scenario['total_execution_cost']):>11,.2f}"
            f"{str(scenario['status']):>14}"
        )

    failed_scenarios = [
        scenario
        for scenario in result.scenarios
        if not scenario["success"]
    ]

    if failed_scenarios:
        print()
        print("FAILED SCENARIOS")
        print("-" * 140)

        for scenario in failed_scenarios:
            print(
                f"- {scenario['scenario_name']}: "
                f"{scenario['error_type']} - "
                f"{scenario['error_message']}"
            )

    print()
    print("VALIDATION CHECKS")
    print("-" * 140)

    all_paths_match = (
        result.path_consistency_percent
        == 100.0
    )

    all_scenarios_profitable = (
        result.profitable_scenarios
        == result.successful_scenarios
        and result.successful_scenarios > 0
    )

    no_failed_scenarios = (
        result.failed_scenarios == 0
    )

    worst_return_positive = (
        result.worst_net_return_percent > 0
    )

    minimum_acceptable_ratio = (
        result.acceptable_percent >= 50.0
    )

    print(
        f"All trade paths match        : "
        f"{all_paths_match}"
    )

    print(
        f"No failed scenarios          : "
        f"{no_failed_scenarios}"
    )

    print(
        f"All scenarios profitable     : "
        f"{all_scenarios_profitable}"
    )

    print(
        f"Worst return is positive     : "
        f"{worst_return_positive}"
    )

    print(
        f"Acceptable scenarios >= 50%  : "
        f"{minimum_acceptable_ratio}"
    )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Report file                  : "
        f"{report_path}"
    )

    print(
        f"Latest file                  : "
        f"{latest_path}"
    )

    print("=" * 140)


def main() -> None:
    """
    AI Stock Bot V7.9 Execution Consistency 테스트입니다.

    비용 없는 기준 거래 경로를 먼저 생성한 뒤,
    모든 비용 시나리오에서 같은 진입일·청산일·
    시장가격·청산 사유를 사용합니다.

    수수료와 슬리피지만 변경하므로 순수한
    거래 비용 민감도를 비교할 수 있습니다.
    """

    symbol = "AAPL"

    print_test_header()

    scenarios: list[
        dict[str, Any]
    ] = [
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

    try:
        result = run_execution_consistency_validation(
            symbol=symbol,

            period="10y",
            interval="1d",

            initial_cash=10_000.0,
            position_percent=20.0,

            # V7.6 Multi-Period Robustness에서
            # 선택된 AGGRESSIVE 전략입니다.
            entry_score=62.0,
            exit_score=44.0,

            stop_atr_multiple=1.50,
            target_atr_multiple=2.25,

            maximum_holding_days=20,

            scenarios=scenarios,
        )

        print_execution_consistency_result(
            result
        )

        (
            report_path,
            latest_path,
        ) = save_execution_consistency_result(
            result
        )

        print_test_summary(
            result=result,
            report_path=report_path,
            latest_path=latest_path,
        )

        # -----------------------------------------------------
        # 결과 구조 자동 확인
        # -----------------------------------------------------
        if (
            result.successful_scenarios
            + result.failed_scenarios
            != result.total_scenarios
        ):
            raise RuntimeError(
                "성공·실패 시나리오 합계가 "
                "전체 시나리오 수와 다릅니다."
            )

        if (
            result.matching_trade_paths
            + result.mismatched_trade_paths
            != result.successful_scenarios
        ):
            raise RuntimeError(
                "일치·불일치 거래 경로 합계가 "
                "성공한 시나리오 수와 다릅니다."
            )

        for scenario in result.scenarios:
            if not scenario["success"]:
                continue

            if (
                int(
                    scenario[
                        "total_trades"
                    ]
                )
                != result.baseline_trade_count
            ):
                raise RuntimeError(
                    f"{scenario['scenario_name']}의 "
                    "거래 횟수가 기준 거래 횟수와 "
                    "일치하지 않습니다."
                )

            if not bool(
                scenario[
                    "trade_path_match"
                ]
            ):
                raise RuntimeError(
                    f"{scenario['scenario_name']}의 "
                    "거래 경로가 기준 경로와 "
                    "일치하지 않습니다."
                )

        print()
        print(
            "V7.9 execution consistency test "
            "completed successfully."
        )

        print(
            "모든 비용 조건에서 동일한 거래 경로를 "
            "사용했는지 자동 검증했습니다."
        )

        print(
            "주의: 이 결과는 과거 데이터 기반 체결 "
            "시뮬레이션이며 실제 주문 체결 또는 "
            "미래 수익을 보장하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 Execution Consistency "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V7.9 EXECUTION CONSISTENCY ERROR"
        )
        print("=" * 140)

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