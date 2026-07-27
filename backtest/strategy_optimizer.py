import json
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np

from backtest.recommendation_backtester import (
    StrategyBacktestResult,
    run_recommendation_backtest,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "optimization"
)


@dataclass
class OptimizationTrial:
    """
    한 가지 파라미터 조합의 백테스트 결과입니다.
    """

    trial_number: int

    entry_score: float
    exit_score: float

    stop_atr_multiple: float
    target_atr_multiple: float

    maximum_holding_days: int
    position_percent: float

    success: bool

    strategy_return_percent: float
    buy_hold_return_percent: float

    total_trades: int
    win_rate_percent: float

    maximum_drawdown_percent: float
    sharpe_ratio: float
    profit_factor: float

    average_trade_return_percent: float

    optimization_score: float

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyOptimizationResult:
    """
    한 종목의 전략 파라미터 최적화 결과입니다.
    """

    version: str

    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    total_trials: int
    successful_trials: int
    failed_trials: int

    period: str
    interval: str
    initial_cash: float
    commission_per_trade: float

    best_trial: dict[str, Any] | None

    top_trials: list[dict[str, Any]]
    all_trials: list[dict[str, Any]]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    값을 안전하게 float로 변환합니다.
    """

    try:
        converted = float(value)

        if np.isnan(converted):
            return default

        if np.isinf(converted):
            return default

        return converted

    except (
        TypeError,
        ValueError,
    ):
        return default


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


def calculate_optimization_score(
    result: StrategyBacktestResult,
    minimum_trades: int = 30,
) -> float:
    """
    최적 조합을 선택하기 위한 종합 점수입니다.

    수익률만 높은 전략이 선택되지 않도록
    Sharpe Ratio, 최대 낙폭, Profit Factor,
    승률 및 거래 횟수를 함께 평가합니다.
    """

    if not result.success:
        return 0.0

    strategy_return = safe_float(
        result.total_return_percent
    )

    sharpe_ratio = safe_float(
        result.sharpe_ratio
    )

    drawdown = abs(
        safe_float(
            result.maximum_drawdown_percent
        )
    )

    profit_factor = safe_float(
        result.profit_factor
    )

    win_rate = safe_float(
        result.win_rate_percent
    )

    total_trades = int(
        result.total_trades
    )

    average_trade_return = safe_float(
        result.average_trade_return_percent
    )

    score = 0.0

    # 전략 총수익률: 최대 30점
    score += min(
        30.0,
        max(
            -20.0,
            strategy_return / 5.0,
        ),
    )

    # Sharpe Ratio: 최대 25점
    score += min(
        25.0,
        max(
            -10.0,
            sharpe_ratio * 12.0,
        ),
    )

    # 최대 낙폭: 최대 20점
    if drawdown <= 5.0:
        score += 20.0

    elif drawdown <= 10.0:
        score += 16.0

    elif drawdown <= 15.0:
        score += 11.0

    elif drawdown <= 20.0:
        score += 6.0

    elif drawdown <= 30.0:
        score += 1.0

    else:
        score -= 10.0

    # Profit Factor: 최대 15점
    if profit_factor >= 2.0:
        score += 15.0

    elif profit_factor >= 1.7:
        score += 12.0

    elif profit_factor >= 1.4:
        score += 9.0

    elif profit_factor >= 1.2:
        score += 5.0

    elif profit_factor >= 1.0:
        score += 1.0

    else:
        score -= 8.0

    # 승률: 최대 8점
    if win_rate >= 60.0:
        score += 8.0

    elif win_rate >= 55.0:
        score += 6.0

    elif win_rate >= 50.0:
        score += 4.0

    elif win_rate >= 45.0:
        score += 1.0

    else:
        score -= 4.0

    # 평균 거래수익률
    if average_trade_return >= 2.0:
        score += 5.0

    elif average_trade_return >= 1.0:
        score += 3.0

    elif average_trade_return > 0:
        score += 1.0

    else:
        score -= 4.0

    # 표본이 너무 적으면 큰 감점
    if total_trades < 10:
        score -= 25.0

    elif total_trades < minimum_trades:
        score -= 12.0

    elif total_trades >= 100:
        score += 3.0

    return round(
        max(
            0.0,
            min(
                100.0,
                score,
            ),
        ),
        2,
    )


def build_trial(
    trial_number: int,
    result: StrategyBacktestResult,
    entry_score: float,
    exit_score: float,
    stop_atr_multiple: float,
    target_atr_multiple: float,
    maximum_holding_days: int,
    position_percent: float,
    minimum_trades: int,
) -> OptimizationTrial:
    """
    백테스트 결과를 최적화 Trial로 변환합니다.
    """

    optimization_score = (
        calculate_optimization_score(
            result=result,
            minimum_trades=minimum_trades,
        )
    )

    return OptimizationTrial(
        trial_number=trial_number,

        entry_score=entry_score,
        exit_score=exit_score,

        stop_atr_multiple=stop_atr_multiple,
        target_atr_multiple=target_atr_multiple,

        maximum_holding_days=maximum_holding_days,
        position_percent=position_percent,

        success=result.success,

        strategy_return_percent=(
            result.total_return_percent
        ),

        buy_hold_return_percent=(
            result.buy_hold_return_percent
        ),

        total_trades=result.total_trades,

        win_rate_percent=(
            result.win_rate_percent
        ),

        maximum_drawdown_percent=(
            result.maximum_drawdown_percent
        ),

        sharpe_ratio=result.sharpe_ratio,

        profit_factor=result.profit_factor,

        average_trade_return_percent=(
            result.average_trade_return_percent
        ),

        optimization_score=(
            optimization_score
        ),

        error_type=result.error_type,
        error_message=result.error_message,
    )


def run_strategy_optimization(
    symbol: str,
    period: str = "10y",
    interval: str = "1d",
    initial_cash: float = 10_000.0,
    commission_per_trade: float = 0.0,
    entry_scores: list[float] | None = None,
    exit_scores: list[float] | None = None,
    stop_atr_multiples: list[float] | None = None,
    target_atr_multiples: list[float] | None = None,
    maximum_holding_days_list: list[int] | None = None,
    position_percents: list[float] | None = None,
    minimum_trades: int = 30,
    top_n: int = 10,
) -> StrategyOptimizationResult:
    """
    여러 전략 파라미터 조합을 자동으로 시험합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if entry_scores is None:
        entry_scores = [
            64.0,
            68.0,
            72.0,
        ]

    if exit_scores is None:
        exit_scores = [
            38.0,
            42.0,
            46.0,
        ]

    if stop_atr_multiples is None:
        stop_atr_multiples = [
            1.25,
            1.5,
            2.0,
        ]

    if target_atr_multiples is None:
        target_atr_multiples = [
            2.5,
            3.0,
            4.0,
        ]

    if maximum_holding_days_list is None:
        maximum_holding_days_list = [
            10,
            20,
            30,
        ]

    if position_percents is None:
        position_percents = [
            20.0,
        ]

    if top_n < 1:
        raise ValueError(
            "top_n은 1 이상이어야 합니다."
        )

    parameter_combinations = list(
        product(
            entry_scores,
            exit_scores,
            stop_atr_multiples,
            target_atr_multiples,
            maximum_holding_days_list,
            position_percents,
        )
    )

    started_at = datetime.now()

    trials: list[
        OptimizationTrial
    ] = []

    total_trials = len(
        parameter_combinations
    )

    print()
    print("=" * 92)
    print(
        f"{normalized_symbol} V7.2 "
        "STRATEGY PARAMETER OPTIMIZATION"
    )
    print("=" * 92)

    print(
        f"Period               : "
        f"{period}"
    )

    print(
        f"Total trials         : "
        f"{total_trials}"
    )

    print(
        f"Minimum trades       : "
        f"{minimum_trades}"
    )

    print("=" * 92)

    for trial_number, parameters in enumerate(
        parameter_combinations,
        start=1,
    ):
        (
            entry_score,
            exit_score,
            stop_atr_multiple,
            target_atr_multiple,
            maximum_holding_days,
            position_percent,
        ) = parameters

        print(
            f"[{trial_number:>3}/{total_trials}] "
            f"Entry {entry_score:.0f} | "
            f"Exit {exit_score:.0f} | "
            f"Stop {stop_atr_multiple:.2f} ATR | "
            f"Target {target_atr_multiple:.2f} ATR | "
            f"Hold {maximum_holding_days} | "
            f"Position {position_percent:.0f}%"
        )

        result = run_recommendation_backtest(
            symbol=normalized_symbol,

            period=period,
            interval=interval,

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

            commission_per_trade=(
                commission_per_trade
            ),
        )

        trial = build_trial(
            trial_number=trial_number,
            result=result,

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

            position_percent=(
                position_percent
            ),

            minimum_trades=minimum_trades,
        )

        trials.append(
            trial
        )

        if trial.success:
            print(
                f"      Score "
                f"{trial.optimization_score:.2f} | "
                f"Return "
                f"{trial.strategy_return_percent:.2f}% | "
                f"Sharpe "
                f"{trial.sharpe_ratio:.2f} | "
                f"DD "
                f"{trial.maximum_drawdown_percent:.2f}% | "
                f"Trades "
                f"{trial.total_trades}"
            )

        else:
            print(
                f"      FAILED: "
                f"{trial.error_type} - "
                f"{trial.error_message}"
            )

    successful_trials = [
        trial
        for trial in trials
        if trial.success
    ]

    failed_trials = [
        trial
        for trial in trials
        if not trial.success
    ]

    successful_trials.sort(
        key=lambda trial: (
            trial.optimization_score,
            trial.sharpe_ratio,
            trial.strategy_return_percent,
            -abs(
                trial.maximum_drawdown_percent
            ),
        ),
        reverse=True,
    )

    top_trials = successful_trials[
        :top_n
    ]

    best_trial = (
        top_trials[0].to_dict()
        if top_trials
        else None
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return StrategyOptimizationResult(
        version="V7.2",

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

        total_trials=total_trials,

        successful_trials=len(
            successful_trials
        ),

        failed_trials=len(
            failed_trials
        ),

        period=period,
        interval=interval,

        initial_cash=round(
            initial_cash,
            2,
        ),

        commission_per_trade=round(
            commission_per_trade,
            2,
        ),

        best_trial=best_trial,

        top_trials=[
            trial.to_dict()
            for trial in top_trials
        ],

        all_trials=[
            trial.to_dict()
            for trial in trials
        ],
    )


def save_optimization_result(
    result: StrategyOptimizationResult,
) -> tuple[Path, Path]:
    """
    전략 최적화 결과를 JSON으로 저장합니다.
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
            f"{result.symbol}_optimization_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_optimization_"
            "latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    result_data = result.to_dict()

    for path in (
        report_path,
        latest_path,
    ):
        with path.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                result_data,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    return (
        report_path,
        latest_path,
    )


def print_optimization_result(
    result: StrategyOptimizationResult,
) -> None:
    """
    최적화 결과 순위표를 출력합니다.
    """

    print()
    print("=" * 124)
    print(
        f"{result.symbol} V7.2 "
        "STRATEGY OPTIMIZATION RESULT"
    )
    print("=" * 124)

    print(
        f"Total trials         : "
        f"{result.total_trials}"
    )

    print(
        f"Successful trials    : "
        f"{result.successful_trials}"
    )

    print(
        f"Failed trials        : "
        f"{result.failed_trials}"
    )

    print(
        f"Elapsed time         : "
        f"{result.elapsed_seconds:.2f} seconds"
    )

    if result.best_trial is None:
        print(
            "Best trial           : N/A"
        )

        print("=" * 124)
        return

    best = result.best_trial

    print()
    print("BEST PARAMETERS")
    print("-" * 124)

    print(
        f"Optimization score   : "
        f"{best['optimization_score']:.2f}/100"
    )

    print(
        f"Entry score          : "
        f"{best['entry_score']:.2f}"
    )

    print(
        f"Exit score           : "
        f"{best['exit_score']:.2f}"
    )

    print(
        f"Stop ATR multiple    : "
        f"{best['stop_atr_multiple']:.2f}"
    )

    print(
        f"Target ATR multiple  : "
        f"{best['target_atr_multiple']:.2f}"
    )

    print(
        f"Maximum holding days : "
        f"{best['maximum_holding_days']}"
    )

    print(
        f"Position percent     : "
        f"{best['position_percent']:.2f}%"
    )

    print()
    print(
        f"Strategy return      : "
        f"{best['strategy_return_percent']:.2f}%"
    )

    print(
        f"Win rate             : "
        f"{best['win_rate_percent']:.2f}%"
    )

    print(
        f"Maximum drawdown     : "
        f"{best['maximum_drawdown_percent']:.2f}%"
    )

    print(
        f"Sharpe ratio         : "
        f"{best['sharpe_ratio']:.2f}"
    )

    print(
        f"Profit factor        : "
        f"{best['profit_factor']:.2f}"
    )

    print(
        f"Total trades         : "
        f"{best['total_trades']}"
    )

    print()
    print("TOP PARAMETER COMBINATIONS")
    print("-" * 124)

    print(
        f"{'Rank':<6}"
        f"{'Score':>8}"
        f"{'Entry':>9}"
        f"{'Exit':>8}"
        f"{'Stop':>9}"
        f"{'Target':>10}"
        f"{'Hold':>8}"
        f"{'Return':>11}"
        f"{'Trades':>9}"
        f"{'WinRate':>10}"
        f"{'Drawdown':>11}"
        f"{'Sharpe':>9}"
        f"{'PF':>8}"
    )

    print("-" * 124)

    for rank, trial in enumerate(
        result.top_trials,
        start=1,
    ):
        print(
            f"{rank:<6}"
            f"{trial['optimization_score']:>8.2f}"
            f"{trial['entry_score']:>9.2f}"
            f"{trial['exit_score']:>8.2f}"
            f"{trial['stop_atr_multiple']:>9.2f}"
            f"{trial['target_atr_multiple']:>10.2f}"
            f"{trial['maximum_holding_days']:>8}"
            f"{trial['strategy_return_percent']:>10.2f}%"
            f"{trial['total_trades']:>9}"
            f"{trial['win_rate_percent']:>9.2f}%"
            f"{trial['maximum_drawdown_percent']:>10.2f}%"
            f"{trial['sharpe_ratio']:>9.2f}"
            f"{trial['profit_factor']:>8.2f}"
        )

    print("=" * 124)

    print(
        "주의: 같은 과거 데이터로 파라미터를 고르면 "
        "과최적화가 발생할 수 있습니다. "
        "다음 단계에서 별도 검증 구간으로 다시 확인해야 합니다."
    )