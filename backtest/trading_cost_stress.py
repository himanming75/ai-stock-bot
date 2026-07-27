import json
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

from backtest.out_of_sample_validator import (
    clean_market_data,
    format_date,
    run_backtest_with_dataframe,
    safe_float,
)
from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "trading_cost_stress"
)


@dataclass
class TradingCostScenario:
    """
    하나의 거래 비용 테스트 조건입니다.
    """

    scenario_number: int

    commission_per_order: float
    slippage_percent_per_order: float

    success: bool

    gross_return_percent: float
    net_return_percent: float
    return_reduction_percent: float

    gross_sharpe_ratio: float
    estimated_net_sharpe_ratio: float

    gross_drawdown_percent: float
    estimated_net_drawdown_percent: float

    gross_profit_factor: float
    estimated_net_profit_factor: float

    total_trades: int
    estimated_orders: int

    estimated_trade_notional: float

    estimated_commission_cost: float
    estimated_slippage_cost: float
    estimated_total_cost: float

    total_cost_percent: float
    cost_per_trade: float

    profitable_after_cost: bool
    acceptable_after_cost: bool

    stress_score: float
    status: str

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TradingCostStressResult:
    """
    전체 거래 비용 스트레스 테스트 결과입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    full_start_date: str
    full_end_date: str
    total_rows: int

    initial_cash: float
    position_percent: float

    strategy_parameters: dict[str, Any]

    total_scenarios: int
    successful_scenarios: int
    failed_scenarios: int

    profitable_scenarios: int
    acceptable_scenarios: int

    profitable_percent: float
    acceptable_percent: float

    baseline_return_percent: float
    baseline_sharpe_ratio: float
    baseline_drawdown_percent: float
    baseline_profit_factor: float
    baseline_total_trades: int

    average_net_return_percent: float
    worst_net_return_percent: float

    average_net_sharpe_ratio: float
    worst_net_sharpe_ratio: float

    average_net_drawdown_percent: float
    worst_net_drawdown_percent: float

    average_total_cost: float
    maximum_total_cost: float

    average_return_reduction_percent: float
    maximum_return_reduction_percent: float

    break_even_scenario: dict[str, Any] | None
    worst_scenario: dict[str, Any] | None

    validation_status: str
    cost_robustness_score: float
    overfitting_warning: bool

    reasons: list[str]
    warnings: list[str]

    scenarios: list[dict[str, Any]]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정리합니다.
    """

    normalized = (
        str(symbol)
        .upper()
        .strip()
    )

    if not normalized:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    return normalized


def safe_average(
    values: list[float],
) -> float:
    """
    평균을 안전하게 계산합니다.
    """

    if not values:
        return 0.0

    return round(
        sum(values) / len(values),
        2,
    )


def estimate_net_sharpe(
    gross_return_percent: float,
    net_return_percent: float,
    gross_sharpe_ratio: float,
) -> float:
    """
    거래 비용 반영 후 Sharpe를 추정합니다.

    기존 백테스트의 일별 자산 곡선을 직접 수정하지 않고
    총수익 감소 비율을 이용하는 보수적 추정 방식입니다.
    """

    if gross_return_percent == 0:
        return round(
            gross_sharpe_ratio,
            2,
        )

    return_ratio = (
        net_return_percent
        / gross_return_percent
    )

    adjusted_sharpe = (
        gross_sharpe_ratio
        * return_ratio
    )

    return round(
        adjusted_sharpe,
        2,
    )


def estimate_net_profit_factor(
    gross_profit_factor: float,
    gross_return_percent: float,
    return_reduction_percent: float,
) -> float:
    """
    거래 비용에 따른 Profit Factor 감소치를 추정합니다.
    """

    if gross_profit_factor <= 0:
        return 0.0

    gross_strength = max(
        abs(gross_return_percent),
        1.0,
    )

    reduction_ratio = min(
        return_reduction_percent
        / gross_strength,
        1.0,
    )

    estimated = (
        gross_profit_factor
        * (
            1.0
            - reduction_ratio * 0.75
        )
    )

    return round(
        max(
            estimated,
            0.0,
        ),
        2,
    )


def calculate_stress_score(
    net_return_percent: float,
    estimated_net_sharpe_ratio: float,
    estimated_net_drawdown_percent: float,
    estimated_net_profit_factor: float,
    return_reduction_percent: float,
    profitable_after_cost: bool,
) -> float:
    """
    거래 비용 적용 후 종합 점수를 계산합니다.
    """

    score = 0.0

    if net_return_percent >= 15.0:
        score += 30.0

    elif net_return_percent >= 10.0:
        score += 25.0

    elif net_return_percent >= 5.0:
        score += 20.0

    elif net_return_percent > 0:
        score += 12.0

    if estimated_net_sharpe_ratio >= 1.0:
        score += 25.0

    elif estimated_net_sharpe_ratio >= 0.70:
        score += 20.0

    elif estimated_net_sharpe_ratio >= 0.40:
        score += 12.0

    elif estimated_net_sharpe_ratio > 0:
        score += 5.0

    drawdown = abs(
        estimated_net_drawdown_percent
    )

    if drawdown <= 7.0:
        score += 20.0

    elif drawdown <= 10.0:
        score += 15.0

    elif drawdown <= 15.0:
        score += 10.0

    elif drawdown <= 20.0:
        score += 5.0

    if estimated_net_profit_factor >= 1.50:
        score += 15.0

    elif estimated_net_profit_factor >= 1.20:
        score += 10.0

    elif estimated_net_profit_factor >= 1.0:
        score += 5.0

    if return_reduction_percent <= 1.0:
        score += 10.0

    elif return_reduction_percent <= 3.0:
        score += 7.0

    elif return_reduction_percent <= 5.0:
        score += 3.0

    if not profitable_after_cost:
        score = min(
            score,
            35.0,
        )

    return round(
        max(
            min(
                score,
                100.0,
            ),
            0.0,
        ),
        2,
    )


def determine_scenario_status(
    net_return_percent: float,
    estimated_net_sharpe_ratio: float,
    estimated_net_profit_factor: float,
    estimated_net_drawdown_percent: float,
) -> str:
    """
    개별 비용 조건의 상태를 결정합니다.
    """

    if (
        net_return_percent > 0
        and estimated_net_sharpe_ratio >= 0.70
        and estimated_net_profit_factor >= 1.20
        and abs(
            estimated_net_drawdown_percent
        ) <= 12.0
    ):
        return "ROBUST"

    if (
        net_return_percent > 0
        and estimated_net_sharpe_ratio >= 0.40
        and estimated_net_profit_factor >= 1.05
        and abs(
            estimated_net_drawdown_percent
        ) <= 18.0
    ):
        return "ACCEPTABLE"

    if net_return_percent > 0:
        return "WEAK"

    return "UNPROFITABLE"


def evaluate_overall_result(
    scenarios: list[TradingCostScenario],
    profitable_percent: float,
    acceptable_percent: float,
    average_net_return: float,
    worst_net_return: float,
    average_return_reduction: float,
) -> tuple[
    str,
    float,
    bool,
    list[str],
    list[str],
]:
    """
    전체 거래 비용 강건성을 평가합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    score = 0.0

    if profitable_percent >= 90.0:
        score += 25.0

        reasons.append(
            "대부분의 거래 비용 조건에서 "
            "플러스 수익을 유지했습니다."
        )

    elif profitable_percent >= 75.0:
        score += 18.0

    elif profitable_percent >= 50.0:
        score += 10.0

    else:
        warnings.append(
            "거래 비용 적용 후 플러스 수익을 "
            "유지한 조건이 절반 미만입니다."
        )

    if acceptable_percent >= 75.0:
        score += 25.0

        reasons.append(
            "대부분의 비용 조건에서 "
            "최소 품질 기준을 통과했습니다."
        )

    elif acceptable_percent >= 50.0:
        score += 15.0

    else:
        warnings.append(
            "거래 비용 적용 후 품질 기준을 "
            "통과한 조건이 충분하지 않습니다."
        )

    if average_net_return >= 10.0:
        score += 20.0

    elif average_net_return >= 5.0:
        score += 15.0

    elif average_net_return > 0:
        score += 8.0

    else:
        warnings.append(
            "평균 비용 반영 수익률이 "
            "0% 이하입니다."
        )

    if worst_net_return > 0:
        score += 15.0

        reasons.append(
            "가장 높은 거래 비용 조건에서도 "
            "플러스 수익을 유지했습니다."
        )

    else:
        warnings.append(
            "일부 높은 비용 조건에서 "
            "전략 수익이 마이너스로 전환됩니다."
        )

    if average_return_reduction <= 2.0:
        score += 15.0

        reasons.append(
            "평균 거래 비용으로 인한 "
            "수익 감소 폭이 비교적 작습니다."
        )

    elif average_return_reduction <= 5.0:
        score += 8.0

    else:
        warnings.append(
            "거래 비용으로 인한 수익 감소 폭이 큽니다."
        )

    score = round(
        min(
            score,
            100.0,
        ),
        2,
    )

    overfitting_warning = (
        profitable_percent < 75.0
        or acceptable_percent < 50.0
        or worst_net_return <= 0
    )

    if (
        score >= 80.0
        and not overfitting_warning
    ):
        status = "ROBUST"

    elif score >= 60.0:
        status = "ACCEPTABLE"

    elif score >= 40.0:
        status = "WEAK"

    else:
        status = "COST_SENSITIVE"

    return (
        status,
        score,
        overfitting_warning,
        reasons,
        warnings,
    )


def run_trading_cost_stress_test(
    symbol: str,

    period: str = "10y",
    interval: str = "1d",

    initial_cash: float = 10_000.0,

    entry_score: float = 62.0,
    exit_score: float = 44.0,

    stop_atr_multiple: float = 1.50,
    target_atr_multiple: float = 2.25,

    maximum_holding_days: int = 20,
    position_percent: float = 20.0,

    commission_values: list[float] | None = None,
    slippage_percent_values: list[float] | None = None,

    minimum_net_sharpe: float = 0.40,
    minimum_net_profit_factor: float = 1.05,
    maximum_drawdown_limit: float = 18.0,
) -> TradingCostStressResult:
    """
    수수료와 슬리피지 조건별로 전략 성과를 검사합니다.

    주의:
    슬리피지는 기존 백테스트의 체결 가격을 직접 변경하지 않고,
    예상 거래 금액과 주문 횟수를 이용해 비용으로 추정합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if commission_values is None:
        commission_values = [
            0.0,
            1.0,
            2.0,
        ]

    if slippage_percent_values is None:
        slippage_percent_values = [
            0.00,
            0.05,
            0.10,
            0.20,
        ]

    started_at = datetime.now()

    print()
    print("=" * 118)
    print(
        f"{normalized_symbol} V7.7 "
        "TRADING COST STRESS TEST"
    )
    print("=" * 118)

    print(
        "Downloading complete market data..."
    )

    data = get_history(
        symbol=normalized_symbol,
        period=period,
        interval=interval,
    )

    data = clean_market_data(
        data
    )

    print(
        f"Full period              : "
        f"{format_date(data.index[0])} "
        f"to {format_date(data.index[-1])}"
    )

    print(
        f"Rows                     : "
        f"{len(data)}"
    )

    print(
        f"Strategy                 : "
        f"Entry {entry_score}, "
        f"Exit {exit_score}, "
        f"Stop {stop_atr_multiple}, "
        f"Target {target_atr_multiple}, "
        f"Hold {maximum_holding_days}"
    )

    combinations = list(
        product(
            commission_values,
            slippage_percent_values,
        )
    )

    print(
        f"Total cost scenarios     : "
        f"{len(combinations)}"
    )

    print("=" * 118)

    baseline_result = (
        run_backtest_with_dataframe(
            symbol=normalized_symbol,
            data=data,

            initial_cash=initial_cash,
            position_percent=position_percent,

            entry_score=entry_score,
            exit_score=exit_score,

            stop_atr_multiple=(
                stop_atr_multiple
            ),

            target_atr_multiple=(
                target_atr_multiple
            ),

            maximum_holding_days=(
                maximum_holding_days
            ),

            commission_per_trade=0.0,

            dataset_name=(
                "TRADING_COST_BASELINE"
            ),
        )
    )

    if not baseline_result.success:
        raise RuntimeError(
            baseline_result.error_message
            or "기본 백테스트 실행에 실패했습니다."
        )

    gross_return = safe_float(
        baseline_result.total_return_percent
    )

    gross_sharpe = safe_float(
        baseline_result.sharpe_ratio
    )

    gross_drawdown = safe_float(
        baseline_result.maximum_drawdown_percent
    )

    gross_profit_factor = safe_float(
        baseline_result.profit_factor
    )

    total_trades = int(
        baseline_result.total_trades
    )

    estimated_orders = (
        total_trades * 2
    )

    estimated_trade_notional = (
        initial_cash
        * (
            position_percent / 100.0
        )
    )

    scenarios: list[
        TradingCostScenario
    ] = []

    for scenario_number, (
        commission_per_order,
        slippage_percent,
    ) in enumerate(
        combinations,
        start=1,
    ):
        try:
            commission_cost = (
                estimated_orders
                * commission_per_order
            )

            slippage_cost = (
                estimated_orders
                * estimated_trade_notional
                * (
                    slippage_percent
                    / 100.0
                )
            )

            total_cost = (
                commission_cost
                + slippage_cost
            )

            total_cost_percent = (
                total_cost
                / initial_cash
                * 100.0
            )

            net_return = (
                gross_return
                - total_cost_percent
            )

            return_reduction = (
                gross_return
                - net_return
            )

            estimated_net_sharpe = (
                estimate_net_sharpe(
                    gross_return_percent=(
                        gross_return
                    ),

                    net_return_percent=(
                        net_return
                    ),

                    gross_sharpe_ratio=(
                        gross_sharpe
                    ),
                )
            )

            estimated_net_drawdown = round(
                gross_drawdown
                - total_cost_percent,
                2,
            )

            estimated_net_profit_factor = (
                estimate_net_profit_factor(
                    gross_profit_factor=(
                        gross_profit_factor
                    ),

                    gross_return_percent=(
                        gross_return
                    ),

                    return_reduction_percent=(
                        return_reduction
                    ),
                )
            )

            profitable_after_cost = (
                net_return > 0
            )

            acceptable_after_cost = (
                net_return > 0
                and estimated_net_sharpe
                >= minimum_net_sharpe
                and estimated_net_profit_factor
                >= minimum_net_profit_factor
                and abs(
                    estimated_net_drawdown
                )
                <= maximum_drawdown_limit
            )

            stress_score = (
                calculate_stress_score(
                    net_return_percent=(
                        net_return
                    ),

                    estimated_net_sharpe_ratio=(
                        estimated_net_sharpe
                    ),

                    estimated_net_drawdown_percent=(
                        estimated_net_drawdown
                    ),

                    estimated_net_profit_factor=(
                        estimated_net_profit_factor
                    ),

                    return_reduction_percent=(
                        return_reduction
                    ),

                    profitable_after_cost=(
                        profitable_after_cost
                    ),
                )
            )

            status = (
                determine_scenario_status(
                    net_return_percent=(
                        net_return
                    ),

                    estimated_net_sharpe_ratio=(
                        estimated_net_sharpe
                    ),

                    estimated_net_profit_factor=(
                        estimated_net_profit_factor
                    ),

                    estimated_net_drawdown_percent=(
                        estimated_net_drawdown
                    ),
                )
            )

            scenario = TradingCostScenario(
                scenario_number=(
                    scenario_number
                ),

                commission_per_order=(
                    commission_per_order
                ),

                slippage_percent_per_order=(
                    slippage_percent
                ),

                success=True,

                gross_return_percent=(
                    gross_return
                ),

                net_return_percent=round(
                    net_return,
                    2,
                ),

                return_reduction_percent=round(
                    return_reduction,
                    2,
                ),

                gross_sharpe_ratio=(
                    gross_sharpe
                ),

                estimated_net_sharpe_ratio=(
                    estimated_net_sharpe
                ),

                gross_drawdown_percent=(
                    gross_drawdown
                ),

                estimated_net_drawdown_percent=(
                    estimated_net_drawdown
                ),

                gross_profit_factor=(
                    gross_profit_factor
                ),

                estimated_net_profit_factor=(
                    estimated_net_profit_factor
                ),

                total_trades=(
                    total_trades
                ),

                estimated_orders=(
                    estimated_orders
                ),

                estimated_trade_notional=round(
                    estimated_trade_notional,
                    2,
                ),

                estimated_commission_cost=round(
                    commission_cost,
                    2,
                ),

                estimated_slippage_cost=round(
                    slippage_cost,
                    2,
                ),

                estimated_total_cost=round(
                    total_cost,
                    2,
                ),

                total_cost_percent=round(
                    total_cost_percent,
                    2,
                ),

                cost_per_trade=round(
                    (
                        total_cost
                        / total_trades
                    )
                    if total_trades
                    else 0.0,
                    2,
                ),

                profitable_after_cost=(
                    profitable_after_cost
                ),

                acceptable_after_cost=(
                    acceptable_after_cost
                ),

                stress_score=(
                    stress_score
                ),

                status=status,
            )

            scenarios.append(
                scenario
            )

            print(
                f"[{scenario_number:>2}/"
                f"{len(combinations)}] "
                f"Commission ${commission_per_order:.2f} | "
                f"Slippage {slippage_percent:.2f}% | "
                f"Cost ${total_cost:,.2f} | "
                f"Net Return {net_return:>7.2f}% | "
                f"Sharpe {estimated_net_sharpe:>5.2f} | "
                f"PF {estimated_net_profit_factor:>5.2f} | "
                f"{status}"
            )

        except Exception as error:
            scenarios.append(
                TradingCostScenario(
                    scenario_number=(
                        scenario_number
                    ),

                    commission_per_order=(
                        commission_per_order
                    ),

                    slippage_percent_per_order=(
                        slippage_percent
                    ),

                    success=False,

                    gross_return_percent=(
                        gross_return
                    ),

                    net_return_percent=0.0,
                    return_reduction_percent=0.0,

                    gross_sharpe_ratio=(
                        gross_sharpe
                    ),

                    estimated_net_sharpe_ratio=0.0,

                    gross_drawdown_percent=(
                        gross_drawdown
                    ),

                    estimated_net_drawdown_percent=0.0,

                    gross_profit_factor=(
                        gross_profit_factor
                    ),

                    estimated_net_profit_factor=0.0,

                    total_trades=(
                        total_trades
                    ),

                    estimated_orders=(
                        estimated_orders
                    ),

                    estimated_trade_notional=(
                        estimated_trade_notional
                    ),

                    estimated_commission_cost=0.0,
                    estimated_slippage_cost=0.0,
                    estimated_total_cost=0.0,

                    total_cost_percent=0.0,
                    cost_per_trade=0.0,

                    profitable_after_cost=False,
                    acceptable_after_cost=False,

                    stress_score=0.0,
                    status="FAILED",

                    error_type=type(
                        error
                    ).__name__,

                    error_message=str(
                        error
                    ),
                )
            )

            print(
                f"[{scenario_number:>2}/"
                f"{len(combinations)}] "
                f"FAILED: "
                f"{type(error).__name__} - "
                f"{error}"
            )

    successful = [
        scenario
        for scenario in scenarios
        if scenario.success
    ]

    failed = [
        scenario
        for scenario in scenarios
        if not scenario.success
    ]

    if not successful:
        raise RuntimeError(
            "성공적으로 완료된 비용 테스트가 없습니다."
        )

    profitable = [
        scenario
        for scenario in successful
        if scenario.profitable_after_cost
    ]

    acceptable = [
        scenario
        for scenario in successful
        if scenario.acceptable_after_cost
    ]

    profitable_percent = round(
        len(profitable)
        / len(successful)
        * 100.0,
        2,
    )

    acceptable_percent = round(
        len(acceptable)
        / len(successful)
        * 100.0,
        2,
    )

    net_returns = [
        scenario.net_return_percent
        for scenario in successful
    ]

    net_sharpes = [
        scenario.estimated_net_sharpe_ratio
        for scenario in successful
    ]

    net_drawdowns = [
        scenario.estimated_net_drawdown_percent
        for scenario in successful
    ]

    total_costs = [
        scenario.estimated_total_cost
        for scenario in successful
    ]

    return_reductions = [
        scenario.return_reduction_percent
        for scenario in successful
    ]

    average_net_return = safe_average(
        net_returns
    )

    worst_net_return = round(
        min(net_returns),
        2,
    )

    average_return_reduction = (
        safe_average(
            return_reductions
        )
    )

    (
        validation_status,
        robustness_score,
        overfitting_warning,
        reasons,
        warnings,
    ) = evaluate_overall_result(
        scenarios=successful,

        profitable_percent=(
            profitable_percent
        ),

        acceptable_percent=(
            acceptable_percent
        ),

        average_net_return=(
            average_net_return
        ),

        worst_net_return=(
            worst_net_return
        ),

        average_return_reduction=(
            average_return_reduction
        ),
    )

    successful.sort(
        key=lambda scenario: (
            scenario.net_return_percent,
            scenario.estimated_net_sharpe_ratio,
        )
    )

    worst_scenario = (
        successful[0]
        if successful
        else None
    )

    break_even_candidates = [
        scenario
        for scenario in successful
        if scenario.net_return_percent > 0
    ]

    break_even_candidates.sort(
        key=lambda scenario: (
            scenario.total_cost_percent
        ),
        reverse=True,
    )

    break_even_scenario = (
        break_even_candidates[0]
        if break_even_candidates
        else None
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return TradingCostStressResult(
        version="V7.7",
        symbol=normalized_symbol,

        started_at=(
            started_at.isoformat()
        ),

        finished_at=(
            finished_at.isoformat()
        ),

        elapsed_seconds=round(
            elapsed_seconds,
            2,
        ),

        full_start_date=format_date(
            data.index[0]
        ),

        full_end_date=format_date(
            data.index[-1]
        ),

        total_rows=len(
            data
        ),

        initial_cash=(
            initial_cash
        ),

        position_percent=(
            position_percent
        ),

        strategy_parameters={
            "entry_score": entry_score,
            "exit_score": exit_score,

            "stop_atr_multiple": (
                stop_atr_multiple
            ),

            "target_atr_multiple": (
                target_atr_multiple
            ),

            "maximum_holding_days": (
                maximum_holding_days
            ),

            "position_percent": (
                position_percent
            ),
        },

        total_scenarios=len(
            scenarios
        ),

        successful_scenarios=len(
            successful
        ),

        failed_scenarios=len(
            failed
        ),

        profitable_scenarios=len(
            profitable
        ),

        acceptable_scenarios=len(
            acceptable
        ),

        profitable_percent=(
            profitable_percent
        ),

        acceptable_percent=(
            acceptable_percent
        ),

        baseline_return_percent=(
            gross_return
        ),

        baseline_sharpe_ratio=(
            gross_sharpe
        ),

        baseline_drawdown_percent=(
            gross_drawdown
        ),

        baseline_profit_factor=(
            gross_profit_factor
        ),

        baseline_total_trades=(
            total_trades
        ),

        average_net_return_percent=(
            average_net_return
        ),

        worst_net_return_percent=(
            worst_net_return
        ),

        average_net_sharpe_ratio=(
            safe_average(
                net_sharpes
            )
        ),

        worst_net_sharpe_ratio=round(
            min(net_sharpes),
            2,
        ),

        average_net_drawdown_percent=(
            safe_average(
                net_drawdowns
            )
        ),

        worst_net_drawdown_percent=round(
            min(net_drawdowns),
            2,
        ),

        average_total_cost=(
            safe_average(
                total_costs
            )
        ),

        maximum_total_cost=round(
            max(total_costs),
            2,
        ),

        average_return_reduction_percent=(
            average_return_reduction
        ),

        maximum_return_reduction_percent=round(
            max(return_reductions),
            2,
        ),

        break_even_scenario=(
            break_even_scenario.to_dict()
            if break_even_scenario
            else None
        ),

        worst_scenario=(
            worst_scenario.to_dict()
            if worst_scenario
            else None
        ),

        validation_status=(
            validation_status
        ),

        cost_robustness_score=(
            robustness_score
        ),

        overfitting_warning=(
            overfitting_warning
        ),

        reasons=reasons,
        warnings=warnings,

        scenarios=[
            scenario.to_dict()
            for scenario in scenarios
        ],
    )


def save_trading_cost_stress_result(
    result: TradingCostStressResult,
) -> tuple[Path, Path]:
    """
    결과를 JSON 파일로 저장합니다.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_trading_cost_stress_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_trading_cost_stress_"
            "latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    payload = result.to_dict()

    for path in (
        report_path,
        latest_path,
    ):
        with path.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    return (
        report_path,
        latest_path,
    )


def print_trading_cost_stress_result(
    result: TradingCostStressResult,
) -> None:
    """
    거래 비용 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 132)
    print(
        f"{result.symbol} V7.7 "
        "TRADING COST STRESS RESULT"
    )
    print("=" * 132)

    print(
        f"Full period                : "
        f"{result.full_start_date} "
        f"to {result.full_end_date}"
    )

    print(
        f"Validation status          : "
        f"{result.validation_status}"
    )

    print(
        f"Overfitting warning        : "
        f"{result.overfitting_warning}"
    )

    print(
        f"Cost robustness score      : "
        f"{result.cost_robustness_score:.2f}/100"
    )

    print()
    print("BASELINE PERFORMANCE")
    print("-" * 132)

    print(
        f"Gross return               : "
        f"{result.baseline_return_percent:.2f}%"
    )

    print(
        f"Gross Sharpe               : "
        f"{result.baseline_sharpe_ratio:.2f}"
    )

    print(
        f"Gross drawdown             : "
        f"{result.baseline_drawdown_percent:.2f}%"
    )

    print(
        f"Gross profit factor        : "
        f"{result.baseline_profit_factor:.2f}"
    )

    print(
        f"Total completed trades     : "
        f"{result.baseline_total_trades}"
    )

    print()
    print("COST STRESS SUMMARY")
    print("-" * 132)

    print(
        f"Total scenarios            : "
        f"{result.total_scenarios}"
    )

    print(
        f"Successful scenarios       : "
        f"{result.successful_scenarios}"
    )

    print(
        f"Failed scenarios           : "
        f"{result.failed_scenarios}"
    )

    print(
        f"Profitable scenarios       : "
        f"{result.profitable_scenarios}/"
        f"{result.successful_scenarios} "
        f"({result.profitable_percent:.2f}%)"
    )

    print(
        f"Acceptable scenarios       : "
        f"{result.acceptable_scenarios}/"
        f"{result.successful_scenarios} "
        f"({result.acceptable_percent:.2f}%)"
    )

    print(
        f"Average net return         : "
        f"{result.average_net_return_percent:.2f}%"
    )

    print(
        f"Worst net return           : "
        f"{result.worst_net_return_percent:.2f}%"
    )

    print(
        f"Average net Sharpe         : "
        f"{result.average_net_sharpe_ratio:.2f}"
    )

    print(
        f"Worst net Sharpe           : "
        f"{result.worst_net_sharpe_ratio:.2f}"
    )

    print(
        f"Average net drawdown       : "
        f"{result.average_net_drawdown_percent:.2f}%"
    )

    print(
        f"Worst net drawdown         : "
        f"{result.worst_net_drawdown_percent:.2f}%"
    )

    print(
        f"Average estimated cost     : "
        f"${result.average_total_cost:,.2f}"
    )

    print(
        f"Maximum estimated cost     : "
        f"${result.maximum_total_cost:,.2f}"
    )

    print(
        f"Average return reduction   : "
        f"{result.average_return_reduction_percent:.2f}%p"
    )

    print(
        f"Maximum return reduction   : "
        f"{result.maximum_return_reduction_percent:.2f}%p"
    )

    print()
    print("SCENARIO RESULTS")
    print("-" * 132)

    print(
        f"{'No.':<6}"
        f"{'Commission':>13}"
        f"{'Slippage':>12}"
        f"{'Cost':>14}"
        f"{'Cost %':>10}"
        f"{'Net Return':>13}"
        f"{'Sharpe':>10}"
        f"{'Drawdown':>12}"
        f"{'PF':>8}"
        f"{'Score':>10}"
        f"{'Status':>15}"
    )

    print("-" * 132)

    successful_scenarios = [
        scenario
        for scenario in result.scenarios
        if scenario["success"]
    ]

    successful_scenarios.sort(
        key=lambda scenario: (
            scenario[
                "commission_per_order"
            ],

            scenario[
                "slippage_percent_per_order"
            ],
        )
    )

    for scenario in successful_scenarios:
        print(
            f"{scenario['scenario_number']:<6}"
            f"${scenario['commission_per_order']:>11.2f}"
            f"{scenario['slippage_percent_per_order']:>11.2f}%"
            f"${scenario['estimated_total_cost']:>12,.2f}"
            f"{scenario['total_cost_percent']:>9.2f}%"
            f"{scenario['net_return_percent']:>12.2f}%"
            f"{scenario['estimated_net_sharpe_ratio']:>10.2f}"
            f"{scenario['estimated_net_drawdown_percent']:>11.2f}%"
            f"{scenario['estimated_net_profit_factor']:>8.2f}"
            f"{scenario['stress_score']:>10.2f}"
            f"{scenario['status']:>15}"
        )

    if result.worst_scenario is not None:
        worst = result.worst_scenario

        print()
        print("WORST COST SCENARIO")
        print("-" * 132)

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
            f"Net return                : "
            f"{worst['net_return_percent']:.2f}%"
        )

        print(
            f"Estimated net Sharpe      : "
            f"{worst['estimated_net_sharpe_ratio']:.2f}"
        )

        print(
            f"Estimated net PF          : "
            f"{worst['estimated_net_profit_factor']:.2f}"
        )

        print(
            f"Status                    : "
            f"{worst['status']}"
        )

    if result.reasons:
        print()
        print("REASONS")

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    print("=" * 132)

    print(
        "주의: 슬리피지와 비용은 평균 거래 금액을 이용한 "
        "보수적 추정치이며 실제 브로커 체결 결과와 다를 수 있습니다."
    )