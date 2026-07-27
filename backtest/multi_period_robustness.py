import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

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
    / "multi_period_robustness"
)


@dataclass
class StrategyParameters:
    """
    비교할 전략 파라미터입니다.
    """

    name: str

    entry_score: float
    exit_score: float

    stop_atr_multiple: float
    target_atr_multiple: float

    maximum_holding_days: int
    position_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PeriodBacktestResult:
    """
    특정 기간에 대한 한 전략의 결과입니다.
    """

    period_years: float
    approximate_rows: int

    start_date: str
    end_date: str
    actual_rows: int

    strategy_name: str

    entry_score: float
    exit_score: float

    stop_atr_multiple: float
    target_atr_multiple: float

    maximum_holding_days: int
    position_percent: float

    success: bool

    strategy_return_percent: float
    buy_hold_return_percent: float
    excess_return_percent: float

    sharpe_ratio: float
    maximum_drawdown_percent: float

    profit_factor: float
    win_rate_percent: float
    total_trades: int

    period_score: float

    profitable: bool
    acceptable: bool

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyPeriodSummary:
    """
    여러 기간에 대한 전략 종합 결과입니다.
    """

    strategy_name: str
    parameters: dict[str, Any]

    successful_periods: int
    failed_periods: int

    profitable_periods: int
    acceptable_periods: int

    profitable_period_percent: float
    acceptable_period_percent: float

    average_return_percent: float
    median_return_percent: float

    average_excess_return_percent: float

    average_sharpe_ratio: float
    median_sharpe_ratio: float

    average_drawdown_percent: float
    worst_drawdown_percent: float

    average_profit_factor: float
    average_win_rate_percent: float

    total_trades: int

    average_period_score: float
    minimum_period_score: float

    return_consistency_score: float
    sharpe_consistency_score: float

    overall_score: float
    ranking_status: str

    results: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MultiPeriodRobustnessResult:
    """
    전체 다중 기간 전략 비교 결과입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    full_start_date: str
    full_end_date: str
    total_rows: int

    estimated_trading_days_per_year: int
    requested_periods_years: list[float]

    total_strategies: int
    total_tests: int
    successful_tests: int
    failed_tests: int

    winner_strategy: str | None
    winner_score: float

    runner_up_strategy: str | None
    runner_up_score: float

    score_difference: float

    validation_status: str
    overfitting_warning: bool

    reasons: list[str]
    warnings: list[str]

    strategy_summaries: list[dict[str, Any]]

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


def safe_median(
    values: list[float],
) -> float:
    """
    중앙값을 안전하게 계산합니다.
    """

    if not values:
        return 0.0

    series = pd.Series(
        values,
        dtype="float64",
    )

    return round(
        float(series.median()),
        2,
    )


def calculate_consistency_score(
    values: list[float],
    higher_is_better: bool = True,
) -> float:
    """
    기간별 성과가 얼마나 안정적인지
    0~100점으로 계산합니다.

    표준편차가 작고 평균이 양수이면
    높은 점수를 받습니다.
    """

    if not values:
        return 0.0

    series = pd.Series(
        values,
        dtype="float64",
    )

    average = float(
        series.mean()
    )

    standard_deviation = float(
        series.std(ddof=0)
    )

    if len(values) == 1:
        standard_deviation = 0.0

    if higher_is_better:
        if average <= 0:
            base_score = 20.0
        else:
            base_score = 70.0
    else:
        base_score = 70.0

    variability_penalty = min(
        standard_deviation * 5.0,
        60.0,
    )

    positive_bonus = 0.0

    if higher_is_better:
        positive_count = sum(
            1
            for value in values
            if value > 0
        )

        positive_ratio = (
            positive_count
            / len(values)
        )

        positive_bonus = (
            positive_ratio
            * 30.0
        )

    score = (
        base_score
        + positive_bonus
        - variability_penalty
    )

    return round(
        max(
            min(score, 100.0),
            0.0,
        ),
        2,
    )


def calculate_period_score(
    strategy_return_percent: float,
    excess_return_percent: float,
    sharpe_ratio: float,
    maximum_drawdown_percent: float,
    profit_factor: float,
    total_trades: int,
    minimum_trades: int,
) -> float:
    """
    개별 기간의 종합 점수를 계산합니다.
    """

    score = 0.0

    bounded_return = max(
        min(
            strategy_return_percent,
            30.0,
        ),
        -20.0,
    )

    score += (
        bounded_return + 20.0
    ) / 50.0 * 25.0

    bounded_excess = max(
        min(
            excess_return_percent,
            20.0,
        ),
        -30.0,
    )

    score += (
        bounded_excess + 30.0
    ) / 50.0 * 15.0

    bounded_sharpe = max(
        min(
            sharpe_ratio,
            2.0,
        ),
        -1.0,
    )

    score += (
        bounded_sharpe + 1.0
    ) / 3.0 * 25.0

    drawdown = abs(
        maximum_drawdown_percent
    )

    if drawdown <= 5.0:
        score += 20.0

    elif drawdown <= 10.0:
        score += 15.0

    elif drawdown <= 15.0:
        score += 10.0

    elif drawdown <= 20.0:
        score += 5.0

    if profit_factor >= 2.0:
        score += 10.0

    elif profit_factor >= 1.50:
        score += 8.0

    elif profit_factor >= 1.20:
        score += 6.0

    elif profit_factor >= 1.0:
        score += 3.0

    if total_trades >= minimum_trades:
        score += 5.0

    elif minimum_trades > 0:
        score += (
            total_trades
            / minimum_trades
        ) * 5.0

    return round(
        max(
            min(score, 100.0),
            0.0,
        ),
        2,
    )


def is_period_acceptable(
    strategy_return_percent: float,
    sharpe_ratio: float,
    maximum_drawdown_percent: float,
    profit_factor: float,
    total_trades: int,
    minimum_trades: int,
) -> bool:
    """
    기간별 최소 품질 기준입니다.
    """

    return (
        strategy_return_percent > 0
        and sharpe_ratio >= 0.40
        and abs(
            maximum_drawdown_percent
        ) <= 18.0
        and profit_factor >= 1.05
        and total_trades >= minimum_trades
    )


def create_failed_period_result(
    period_years: float,
    approximate_rows: int,
    period_data: pd.DataFrame,
    strategy: StrategyParameters,
    error: Exception,
) -> PeriodBacktestResult:
    """
    실패한 기간 결과를 생성합니다.
    """

    return PeriodBacktestResult(
        period_years=period_years,
        approximate_rows=approximate_rows,

        start_date=(
            format_date(period_data.index[0])
            if not period_data.empty
            else "N/A"
        ),

        end_date=(
            format_date(period_data.index[-1])
            if not period_data.empty
            else "N/A"
        ),

        actual_rows=len(
            period_data
        ),

        strategy_name=strategy.name,

        entry_score=strategy.entry_score,
        exit_score=strategy.exit_score,

        stop_atr_multiple=(
            strategy.stop_atr_multiple
        ),

        target_atr_multiple=(
            strategy.target_atr_multiple
        ),

        maximum_holding_days=(
            strategy.maximum_holding_days
        ),

        position_percent=(
            strategy.position_percent
        ),

        success=False,

        strategy_return_percent=0.0,
        buy_hold_return_percent=0.0,
        excess_return_percent=0.0,

        sharpe_ratio=0.0,
        maximum_drawdown_percent=0.0,

        profit_factor=0.0,
        win_rate_percent=0.0,
        total_trades=0,

        period_score=0.0,

        profitable=False,
        acceptable=False,

        error_type=type(
            error
        ).__name__,

        error_message=str(
            error
        ),
    )


def build_strategy_summary(
    strategy: StrategyParameters,
    results: list[PeriodBacktestResult],
) -> StrategyPeriodSummary:
    """
    한 전략의 여러 기간 결과를 종합합니다.
    """

    successful = [
        result
        for result in results
        if result.success
    ]

    failed = [
        result
        for result in results
        if not result.success
    ]

    profitable = [
        result
        for result in successful
        if result.profitable
    ]

    acceptable = [
        result
        for result in successful
        if result.acceptable
    ]

    successful_count = len(
        successful
    )

    profitable_percent = (
        round(
            len(profitable)
            / successful_count
            * 100.0,
            2,
        )
        if successful_count
        else 0.0
    )

    acceptable_percent = (
        round(
            len(acceptable)
            / successful_count
            * 100.0,
            2,
        )
        if successful_count
        else 0.0
    )

    returns = [
        result.strategy_return_percent
        for result in successful
    ]

    excess_returns = [
        result.excess_return_percent
        for result in successful
    ]

    sharpes = [
        result.sharpe_ratio
        for result in successful
    ]

    drawdowns = [
        result.maximum_drawdown_percent
        for result in successful
    ]

    profit_factors = [
        result.profit_factor
        for result in successful
    ]

    win_rates = [
        result.win_rate_percent
        for result in successful
    ]

    period_scores = [
        result.period_score
        for result in successful
    ]

    return_consistency = (
        calculate_consistency_score(
            returns
        )
    )

    sharpe_consistency = (
        calculate_consistency_score(
            sharpes
        )
    )

    average_period_score = (
        safe_average(
            period_scores
        )
    )

    consistency_component = (
        return_consistency
        + sharpe_consistency
    ) / 2.0

    overall_score = (
        average_period_score * 0.45
        + profitable_percent * 0.15
        + acceptable_percent * 0.15
        + consistency_component * 0.25
    )

    overall_score = round(
        max(
            min(overall_score, 100.0),
            0.0,
        ),
        2,
    )

    if overall_score >= 80.0:
        ranking_status = "STRONG"

    elif overall_score >= 65.0:
        ranking_status = "ACCEPTABLE"

    elif overall_score >= 50.0:
        ranking_status = "WEAK"

    else:
        ranking_status = "UNSTABLE"

    return StrategyPeriodSummary(
        strategy_name=strategy.name,

        parameters=(
            strategy.to_dict()
        ),

        successful_periods=(
            successful_count
        ),

        failed_periods=len(
            failed
        ),

        profitable_periods=len(
            profitable
        ),

        acceptable_periods=len(
            acceptable
        ),

        profitable_period_percent=(
            profitable_percent
        ),

        acceptable_period_percent=(
            acceptable_percent
        ),

        average_return_percent=(
            safe_average(
                returns
            )
        ),

        median_return_percent=(
            safe_median(
                returns
            )
        ),

        average_excess_return_percent=(
            safe_average(
                excess_returns
            )
        ),

        average_sharpe_ratio=(
            safe_average(
                sharpes
            )
        ),

        median_sharpe_ratio=(
            safe_median(
                sharpes
            )
        ),

        average_drawdown_percent=(
            safe_average(
                drawdowns
            )
        ),

        worst_drawdown_percent=(
            round(
                min(drawdowns),
                2,
            )
            if drawdowns
            else 0.0
        ),

        average_profit_factor=(
            safe_average(
                profit_factors
            )
        ),

        average_win_rate_percent=(
            safe_average(
                win_rates
            )
        ),

        total_trades=sum(
            result.total_trades
            for result in successful
        ),

        average_period_score=(
            average_period_score
        ),

        minimum_period_score=(
            round(
                min(period_scores),
                2,
            )
            if period_scores
            else 0.0
        ),

        return_consistency_score=(
            return_consistency
        ),

        sharpe_consistency_score=(
            sharpe_consistency
        ),

        overall_score=(
            overall_score
        ),

        ranking_status=(
            ranking_status
        ),

        results=[
            result.to_dict()
            for result in results
        ],
    )


def evaluate_comparison(
    summaries: list[StrategyPeriodSummary],
) -> tuple[
    str,
    bool,
    list[str],
    list[str],
]:
    """
    전략 비교 전체 결과를 평가합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if not summaries:
        return (
            "FAILED",
            True,
            [],
            [
                "비교할 전략 결과가 없습니다."
            ],
        )

    winner = summaries[0]

    if winner.profitable_period_percent >= 75.0:
        reasons.append(
            "우승 전략은 대부분의 검증 기간에서 "
            "플러스 수익을 기록했습니다."
        )

    else:
        warnings.append(
            "우승 전략도 플러스 수익 기간이 "
            "충분히 많지 않습니다."
        )

    if winner.acceptable_period_percent >= 75.0:
        reasons.append(
            "우승 전략은 대부분의 기간에서 "
            "최소 품질 기준을 통과했습니다."
        )

    else:
        warnings.append(
            "우승 전략의 품질 기준 통과율이 "
            "75% 미만입니다."
        )

    if winner.return_consistency_score >= 70.0:
        reasons.append(
            "기간별 수익률 일관성이 비교적 좋습니다."
        )

    else:
        warnings.append(
            "기간별 수익률 변동이 커서 "
            "성과 일관성이 낮을 수 있습니다."
        )

    if winner.average_sharpe_ratio >= 0.70:
        reasons.append(
            "평균 Sharpe Ratio가 0.70 이상입니다."
        )

    elif winner.average_sharpe_ratio < 0.40:
        warnings.append(
            "평균 Sharpe Ratio가 0.40 미만입니다."
        )

    if abs(
        winner.worst_drawdown_percent
    ) <= 12.0:
        reasons.append(
            "최악의 기간 낙폭이 12% 이내입니다."
        )

    else:
        warnings.append(
            "일부 기간의 최대 낙폭이 "
            "12%를 초과합니다."
        )

    overfitting_warning = (
        winner.profitable_period_percent < 75.0
        or winner.acceptable_period_percent < 75.0
        or winner.return_consistency_score < 60.0
        or winner.minimum_period_score < 45.0
    )

    if (
        winner.overall_score >= 80.0
        and not overfitting_warning
    ):
        validation_status = "ROBUST"

    elif winner.overall_score >= 65.0:
        validation_status = "ACCEPTABLE"

    elif winner.overall_score >= 50.0:
        validation_status = "WEAK"

    else:
        validation_status = "UNSTABLE"

    return (
        validation_status,
        overfitting_warning,
        reasons,
        warnings,
    )


def run_multi_period_robustness_test(
    symbol: str,
    strategies: list[StrategyParameters],

    period: str = "10y",
    interval: str = "1d",

    periods_years: list[float] | None = None,

    estimated_trading_days_per_year: int = 252,

    initial_cash: float = 10_000.0,
    commission_per_trade: float = 0.0,

    minimum_trades_per_year: int = 8,
) -> MultiPeriodRobustnessResult:
    """
    여러 전략을 최근 1년, 2년, 3년, 5년처럼
    서로 다른 검증 기간에서 비교합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if not strategies:
        raise ValueError(
            "비교할 전략이 없습니다."
        )

    if periods_years is None:
        periods_years = [
            1.0,
            2.0,
            3.0,
            5.0,
        ]

    periods_years = sorted(
        {
            float(value)
            for value in periods_years
            if float(value) > 0
        }
    )

    if not periods_years:
        raise ValueError(
            "검증 기간이 비어 있습니다."
        )

    started_at = datetime.now()

    print()
    print("=" * 118)
    print(
        f"{normalized_symbol} V7.6 "
        "MULTI-PERIOD ROBUSTNESS TEST"
    )
    print("=" * 118)

    print(
        "Downloading complete market data..."
    )

    full_data = get_history(
        symbol=normalized_symbol,
        period=period,
        interval=interval,
    )

    full_data = clean_market_data(
        full_data
    )

    print(
        f"Full period          : "
        f"{format_date(full_data.index[0])} "
        f"to {format_date(full_data.index[-1])}"
    )

    print(
        f"Full rows            : "
        f"{len(full_data)}"
    )

    print(
        f"Strategies           : "
        f"{len(strategies)}"
    )

    print(
        "Test periods         : "
        + ", ".join(
            f"{value:g}y"
            for value in periods_years
        )
    )

    print("=" * 118)

    strategy_results: dict[
        str,
        list[PeriodBacktestResult],
    ] = {
        strategy.name: []
        for strategy in strategies
    }

    total_tests = (
        len(strategies)
        * len(periods_years)
    )

    test_number = 0

    for period_years in periods_years:
        approximate_rows = int(
            period_years
            * estimated_trading_days_per_year
        )

        actual_rows = min(
            approximate_rows,
            len(full_data),
        )

        period_data = (
            full_data
            .iloc[-actual_rows:]
            .copy()
        )

        print()
        print("#" * 118)

        print(
            f"TEST PERIOD: "
            f"{period_years:g} YEAR(S)"
        )

        print(
            f"Dates                : "
            f"{format_date(period_data.index[0])} "
            f"to {format_date(period_data.index[-1])}"
        )

        print(
            f"Rows                 : "
            f"{len(period_data)}"
        )

        print("#" * 118)

        for strategy in strategies:
            test_number += 1

            minimum_trades = max(
                int(
                    minimum_trades_per_year
                    * period_years
                ),
                3,
            )

            print()
            print(
                f"[{test_number}/{total_tests}] "
                f"{strategy.name}"
            )

            try:
                backtest_result = (
                    run_backtest_with_dataframe(
                        symbol=normalized_symbol,

                        data=period_data,

                        initial_cash=initial_cash,

                        position_percent=(
                            strategy.position_percent
                        ),

                        entry_score=(
                            strategy.entry_score
                        ),

                        exit_score=(
                            strategy.exit_score
                        ),

                        stop_atr_multiple=(
                            strategy.stop_atr_multiple
                        ),

                        target_atr_multiple=(
                            strategy.target_atr_multiple
                        ),

                        maximum_holding_days=(
                            strategy.maximum_holding_days
                        ),

                        commission_per_trade=(
                            commission_per_trade
                        ),

                        dataset_name=(
                            f"MULTI_PERIOD_"
                            f"{strategy.name}_"
                            f"{period_years:g}Y"
                        ),
                    )
                )

                if not backtest_result.success:
                    raise RuntimeError(
                        backtest_result.error_message
                        or "백테스트 실행에 실패했습니다."
                    )

                strategy_return = safe_float(
                    backtest_result
                    .total_return_percent
                )

                buy_hold_return = safe_float(
                    backtest_result
                    .buy_hold_return_percent
                )

                excess_return = round(
                    strategy_return
                    - buy_hold_return,
                    2,
                )

                sharpe_ratio = safe_float(
                    backtest_result
                    .sharpe_ratio
                )

                maximum_drawdown = safe_float(
                    backtest_result
                    .maximum_drawdown_percent
                )

                profit_factor = safe_float(
                    backtest_result
                    .profit_factor
                )

                win_rate = safe_float(
                    backtest_result
                    .win_rate_percent
                )

                total_trades = int(
                    backtest_result
                    .total_trades
                )

                period_score = (
                    calculate_period_score(
                        strategy_return_percent=(
                            strategy_return
                        ),

                        excess_return_percent=(
                            excess_return
                        ),

                        sharpe_ratio=(
                            sharpe_ratio
                        ),

                        maximum_drawdown_percent=(
                            maximum_drawdown
                        ),

                        profit_factor=(
                            profit_factor
                        ),

                        total_trades=(
                            total_trades
                        ),

                        minimum_trades=(
                            minimum_trades
                        ),
                    )
                )

                acceptable = (
                    is_period_acceptable(
                        strategy_return_percent=(
                            strategy_return
                        ),

                        sharpe_ratio=(
                            sharpe_ratio
                        ),

                        maximum_drawdown_percent=(
                            maximum_drawdown
                        ),

                        profit_factor=(
                            profit_factor
                        ),

                        total_trades=(
                            total_trades
                        ),

                        minimum_trades=(
                            minimum_trades
                        ),
                    )
                )

                result = PeriodBacktestResult(
                    period_years=period_years,

                    approximate_rows=(
                        approximate_rows
                    ),

                    start_date=format_date(
                        period_data.index[0]
                    ),

                    end_date=format_date(
                        period_data.index[-1]
                    ),

                    actual_rows=len(
                        period_data
                    ),

                    strategy_name=(
                        strategy.name
                    ),

                    entry_score=(
                        strategy.entry_score
                    ),

                    exit_score=(
                        strategy.exit_score
                    ),

                    stop_atr_multiple=(
                        strategy.stop_atr_multiple
                    ),

                    target_atr_multiple=(
                        strategy.target_atr_multiple
                    ),

                    maximum_holding_days=(
                        strategy.maximum_holding_days
                    ),

                    position_percent=(
                        strategy.position_percent
                    ),

                    success=True,

                    strategy_return_percent=(
                        strategy_return
                    ),

                    buy_hold_return_percent=(
                        buy_hold_return
                    ),

                    excess_return_percent=(
                        excess_return
                    ),

                    sharpe_ratio=(
                        sharpe_ratio
                    ),

                    maximum_drawdown_percent=(
                        maximum_drawdown
                    ),

                    profit_factor=(
                        profit_factor
                    ),

                    win_rate_percent=(
                        win_rate
                    ),

                    total_trades=(
                        total_trades
                    ),

                    period_score=(
                        period_score
                    ),

                    profitable=(
                        strategy_return > 0
                    ),

                    acceptable=acceptable,
                )

                strategy_results[
                    strategy.name
                ].append(
                    result
                )

                print(
                    f"Return               : "
                    f"{strategy_return:.2f}%"
                )

                print(
                    f"Buy and hold         : "
                    f"{buy_hold_return:.2f}%"
                )

                print(
                    f"Excess return        : "
                    f"{excess_return:+.2f}%p"
                )

                print(
                    f"Sharpe               : "
                    f"{sharpe_ratio:.2f}"
                )

                print(
                    f"Drawdown             : "
                    f"{maximum_drawdown:.2f}%"
                )

                print(
                    f"Profit factor        : "
                    f"{profit_factor:.2f}"
                )

                print(
                    f"Trades               : "
                    f"{total_trades}"
                )

                print(
                    f"Period score         : "
                    f"{period_score:.2f}/100"
                )

                print(
                    f"Status               : "
                    f"{'ACCEPTABLE' if acceptable else 'WEAK'}"
                )

            except Exception as error:
                failed_result = (
                    create_failed_period_result(
                        period_years=(
                            period_years
                        ),

                        approximate_rows=(
                            approximate_rows
                        ),

                        period_data=(
                            period_data
                        ),

                        strategy=strategy,
                        error=error,
                    )
                )

                strategy_results[
                    strategy.name
                ].append(
                    failed_result
                )

                print(
                    f"FAILED               : "
                    f"{type(error).__name__} - "
                    f"{error}"
                )

    summaries = [
        build_strategy_summary(
            strategy=strategy,

            results=strategy_results[
                strategy.name
            ],
        )
        for strategy in strategies
    ]

    summaries.sort(
        key=lambda summary: (
            summary.overall_score,
            summary.acceptable_period_percent,
            summary.average_sharpe_ratio,
            summary.average_return_percent,
        ),
        reverse=True,
    )

    winner = (
        summaries[0]
        if summaries
        else None
    )

    runner_up = (
        summaries[1]
        if len(summaries) > 1
        else None
    )

    (
        validation_status,
        overfitting_warning,
        reasons,
        warnings,
    ) = evaluate_comparison(
        summaries
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    successful_tests = sum(
        summary.successful_periods
        for summary in summaries
    )

    failed_tests = sum(
        summary.failed_periods
        for summary in summaries
    )

    return MultiPeriodRobustnessResult(
        version="V7.6",

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
            full_data.index[0]
        ),

        full_end_date=format_date(
            full_data.index[-1]
        ),

        total_rows=len(
            full_data
        ),

        estimated_trading_days_per_year=(
            estimated_trading_days_per_year
        ),

        requested_periods_years=(
            periods_years
        ),

        total_strategies=len(
            strategies
        ),

        total_tests=total_tests,

        successful_tests=(
            successful_tests
        ),

        failed_tests=(
            failed_tests
        ),

        winner_strategy=(
            winner.strategy_name
            if winner
            else None
        ),

        winner_score=(
            winner.overall_score
            if winner
            else 0.0
        ),

        runner_up_strategy=(
            runner_up.strategy_name
            if runner_up
            else None
        ),

        runner_up_score=(
            runner_up.overall_score
            if runner_up
            else 0.0
        ),

        score_difference=round(
            (
                winner.overall_score
                - runner_up.overall_score
            )
            if (
                winner
                and runner_up
            )
            else 0.0,
            2,
        ),

        validation_status=(
            validation_status
        ),

        overfitting_warning=(
            overfitting_warning
        ),

        reasons=reasons,
        warnings=warnings,

        strategy_summaries=[
            summary.to_dict()
            for summary in summaries
        ],
    )


def save_multi_period_result(
    result: MultiPeriodRobustnessResult,
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
            f"{result.symbol}_multi_period_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_multi_period_"
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


def print_multi_period_result(
    result: MultiPeriodRobustnessResult,
) -> None:
    """
    전체 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 132)
    print(
        f"{result.symbol} V7.6 "
        "MULTI-PERIOD ROBUSTNESS RESULT"
    )
    print("=" * 132)

    print(
        f"Full period              : "
        f"{result.full_start_date} "
        f"to {result.full_end_date}"
    )

    print(
        f"Validation status        : "
        f"{result.validation_status}"
    )

    print(
        f"Overfitting warning      : "
        f"{result.overfitting_warning}"
    )

    print(
        f"Total tests              : "
        f"{result.total_tests}"
    )

    print(
        f"Successful tests         : "
        f"{result.successful_tests}"
    )

    print(
        f"Failed tests             : "
        f"{result.failed_tests}"
    )

    print()
    print("FINAL RANKING")
    print("-" * 132)

    print(
        f"{'Rank':<6}"
        f"{'Strategy':<22}"
        f"{'Score':>10}"
        f"{'Avg Return':>14}"
        f"{'Avg Excess':>14}"
        f"{'Avg Sharpe':>13}"
        f"{'Worst DD':>12}"
        f"{'Profitable':>13}"
        f"{'Acceptable':>13}"
        f"{'Status':>13}"
    )

    print("-" * 132)

    for rank, summary in enumerate(
        result.strategy_summaries,
        start=1,
    ):
        print(
            f"{rank:<6}"
            f"{summary['strategy_name']:<22}"
            f"{summary['overall_score']:>10.2f}"
            f"{summary['average_return_percent']:>13.2f}%"
            f"{summary['average_excess_return_percent']:>13.2f}%"
            f"{summary['average_sharpe_ratio']:>13.2f}"
            f"{summary['worst_drawdown_percent']:>11.2f}%"
            f"{summary['profitable_period_percent']:>12.2f}%"
            f"{summary['acceptable_period_percent']:>12.2f}%"
            f"{summary['ranking_status']:>13}"
        )

    print()
    print("WINNER")
    print("-" * 132)

    print(
        f"Winner strategy          : "
        f"{result.winner_strategy}"
    )

    print(
        f"Winner score             : "
        f"{result.winner_score:.2f}/100"
    )

    print(
        f"Runner-up strategy       : "
        f"{result.runner_up_strategy}"
    )

    print(
        f"Runner-up score          : "
        f"{result.runner_up_score:.2f}/100"
    )

    print(
        f"Score difference         : "
        f"{result.score_difference:+.2f}"
    )

    for summary in result.strategy_summaries:
        print()
        print(
            f"{summary['strategy_name']} "
            "PERIOD RESULTS"
        )

        print("-" * 132)

        parameters = summary[
            "parameters"
        ]

        print(
            f"Parameters               : "
            f"Entry {parameters['entry_score']}, "
            f"Exit {parameters['exit_score']}, "
            f"Stop {parameters['stop_atr_multiple']}, "
            f"Target {parameters['target_atr_multiple']}, "
            f"Hold {parameters['maximum_holding_days']}"
        )

        print(
            f"Average period score     : "
            f"{summary['average_period_score']:.2f}/100"
        )

        print(
            f"Minimum period score     : "
            f"{summary['minimum_period_score']:.2f}/100"
        )

        print(
            f"Return consistency       : "
            f"{summary['return_consistency_score']:.2f}/100"
        )

        print(
            f"Sharpe consistency       : "
            f"{summary['sharpe_consistency_score']:.2f}/100"
        )

        print()
        print(
            f"{'Period':<10}"
            f"{'Start':<13}"
            f"{'End':<13}"
            f"{'Return':>11}"
            f"{'BuyHold':>11}"
            f"{'Excess':>11}"
            f"{'Sharpe':>9}"
            f"{'DD':>10}"
            f"{'PF':>8}"
            f"{'Trades':>9}"
            f"{'Score':>9}"
            f"{'Status':>12}"
        )

        print("-" * 132)

        for period_result in summary[
            "results"
        ]:
            if not period_result[
                "success"
            ]:
                print(
                    f"{period_result['period_years']:<10g}"
                    f"{period_result['start_date']:<13}"
                    f"{period_result['end_date']:<13}"
                    f"{'FAILED':>97}"
                )
                continue

            status = (
                "ACCEPTABLE"
                if period_result[
                    "acceptable"
                ]
                else "WEAK"
            )

            print(
                f"{period_result['period_years']:<10g}"
                f"{period_result['start_date']:<13}"
                f"{period_result['end_date']:<13}"
                f"{period_result['strategy_return_percent']:>10.2f}%"
                f"{period_result['buy_hold_return_percent']:>10.2f}%"
                f"{period_result['excess_return_percent']:>+10.2f}%"
                f"{period_result['sharpe_ratio']:>9.2f}"
                f"{period_result['maximum_drawdown_percent']:>9.2f}%"
                f"{period_result['profit_factor']:>8.2f}"
                f"{period_result['total_trades']:>9}"
                f"{period_result['period_score']:>9.2f}"
                f"{status:>12}"
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
        "주의: 여러 기간에서의 과거 성과 비교이며 "
        "미래 수익이나 실제 주문 결과를 보장하지 않습니다."
    )