import json
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from backtest.out_of_sample_validator import (
    clean_market_data,
    format_date,
    run_backtest_with_dataframe,
    safe_float,
    split_train_validation_data,
)
from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "parameter_robustness"
)


@dataclass
class ParameterTrialResult:
    """
    하나의 파라미터 조합 테스트 결과입니다.
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
    excess_return_percent: float

    sharpe_ratio: float
    maximum_drawdown_percent: float

    profit_factor: float
    win_rate_percent: float
    total_trades: int

    robustness_score: float

    distance_from_center: float

    profitable: bool
    acceptable: bool

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParameterRobustnessResult:
    """
    전체 파라미터 강건성 검사 결과입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    full_start_date: str
    full_end_date: str

    validation_start_date: str
    validation_end_date: str

    full_rows: int
    training_rows: int
    validation_rows: int

    training_ratio_percent: float
    validation_ratio_percent: float

    center_parameters: dict[str, Any]

    total_trials: int
    successful_trials: int
    failed_trials: int

    profitable_trials: int
    acceptable_trials: int

    profitable_percent: float
    acceptable_percent: float

    average_return_percent: float
    median_return_percent: float

    average_sharpe_ratio: float
    median_sharpe_ratio: float

    average_drawdown_percent: float
    worst_drawdown_percent: float

    average_profit_factor: float
    average_win_rate_percent: float

    best_trial: dict[str, Any] | None
    center_trial: dict[str, Any] | None

    center_return_percent: float
    center_sharpe_ratio: float
    center_drawdown_percent: float

    nearby_average_return_percent: float
    nearby_average_sharpe_ratio: float

    center_vs_nearby_return_difference: float
    center_vs_nearby_sharpe_difference: float

    robust_trial_percent: float
    parameter_robustness_score: float

    validation_status: str
    overfitting_warning: bool

    reasons: list[str]
    warnings: list[str]

    trials: list[dict[str, Any]]

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
        sum(values)
        / len(values),
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
        float(
            series.median()
        ),
        2,
    )


def calculate_parameter_distance(
    entry_score: float,
    exit_score: float,
    stop_atr_multiple: float,
    target_atr_multiple: float,
    maximum_holding_days: int,
    center_entry_score: float,
    center_exit_score: float,
    center_stop_atr_multiple: float,
    center_target_atr_multiple: float,
    center_maximum_holding_days: int,
) -> float:
    """
    중심 파라미터에서 얼마나 떨어졌는지 계산합니다.

    각 파라미터의 단위 차이가 크기 때문에
    정규화된 거리 값을 사용합니다.
    """

    entry_distance = abs(
        entry_score
        - center_entry_score
    ) / 2.0

    exit_distance = abs(
        exit_score
        - center_exit_score
    ) / 2.0

    stop_distance = abs(
        stop_atr_multiple
        - center_stop_atr_multiple
    ) / 0.25

    target_distance = abs(
        target_atr_multiple
        - center_target_atr_multiple
    ) / 0.25

    holding_distance = abs(
        maximum_holding_days
        - center_maximum_holding_days
    ) / 10.0

    total_distance = (
        entry_distance
        + exit_distance
        + stop_distance
        + target_distance
        + holding_distance
    )

    return round(
        total_distance,
        2,
    )


def calculate_trial_score(
    strategy_return_percent: float,
    sharpe_ratio: float,
    maximum_drawdown_percent: float,
    profit_factor: float,
    total_trades: int,
    minimum_trades: int,
) -> float:
    """
    파라미터 조합의 종합 점수를 계산합니다.

    수익률만 높은 조합보다
    Sharpe, 낙폭, Profit Factor와
    거래 횟수가 균형 잡힌 조합을 선호합니다.
    """

    score = 0.0

    return_score = max(
        min(
            strategy_return_percent,
            20.0,
        ),
        -20.0,
    )

    score += (
        return_score
        + 20.0
    ) / 40.0 * 30.0

    sharpe_score = max(
        min(
            sharpe_ratio,
            2.0,
        ),
        -1.0,
    )

    score += (
        sharpe_score
        + 1.0
    ) / 3.0 * 30.0

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
        score += 15.0

    elif profit_factor >= 1.50:
        score += 12.0

    elif profit_factor >= 1.20:
        score += 8.0

    elif profit_factor >= 1.0:
        score += 4.0

    if total_trades >= minimum_trades:
        score += 5.0

    else:
        trade_ratio = (
            total_trades
            / minimum_trades
        )

        score += max(
            trade_ratio,
            0.0,
        ) * 5.0

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


def is_trial_acceptable(
    strategy_return_percent: float,
    sharpe_ratio: float,
    maximum_drawdown_percent: float,
    profit_factor: float,
    total_trades: int,
    minimum_trades: int,
) -> bool:
    """
    파라미터 조합이 최소 품질 기준을
    충족하는지 판단합니다.
    """

    return (
        strategy_return_percent > 0
        and sharpe_ratio >= 0.50
        and abs(
            maximum_drawdown_percent
        ) <= 15.0
        and profit_factor >= 1.10
        and total_trades >= minimum_trades
    )


def build_failed_trial(
    trial_number: int,
    entry_score: float,
    exit_score: float,
    stop_atr_multiple: float,
    target_atr_multiple: float,
    maximum_holding_days: int,
    position_percent: float,
    distance_from_center: float,
    error: Exception,
) -> ParameterTrialResult:
    """
    실패한 파라미터 조합 결과를 만듭니다.
    """

    return ParameterTrialResult(
        trial_number=trial_number,

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

        success=False,

        strategy_return_percent=0.0,
        buy_hold_return_percent=0.0,
        excess_return_percent=0.0,

        sharpe_ratio=0.0,
        maximum_drawdown_percent=0.0,

        profit_factor=0.0,
        win_rate_percent=0.0,
        total_trades=0,

        robustness_score=0.0,

        distance_from_center=(
            distance_from_center
        ),

        profitable=False,
        acceptable=False,

        error_type=type(
            error
        ).__name__,

        error_message=str(
            error
        ),
    )


def evaluate_overall_robustness(
    successful_trials: list[
        ParameterTrialResult
    ],
    profitable_percent: float,
    acceptable_percent: float,
    robust_trial_percent: float,
    average_return: float,
    median_return: float,
    average_sharpe: float,
    worst_drawdown: float,
    center_return: float,
    nearby_average_return: float,
) -> tuple[
    str,
    bool,
    float,
    list[str],
    list[str],
]:
    """
    전체 파라미터 강건성을 평가합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if not successful_trials:
        return (
            "FAILED",
            True,
            0.0,
            [],
            [
                "성공적으로 완료된 파라미터 "
                "테스트가 없습니다."
            ],
        )

    score = 0.0

    if profitable_percent >= 80.0:
        score += 20.0

        reasons.append(
            "80% 이상의 주변 파라미터가 "
            "플러스 수익을 기록했습니다."
        )

    elif profitable_percent >= 60.0:
        score += 15.0

    elif profitable_percent >= 50.0:
        score += 10.0

    else:
        warnings.append(
            "플러스 수익을 기록한 주변 "
            "파라미터가 절반 미만입니다."
        )

    if acceptable_percent >= 70.0:
        score += 20.0

        reasons.append(
            "대부분의 주변 파라미터가 "
            "최소 품질 기준을 통과했습니다."
        )

    elif acceptable_percent >= 50.0:
        score += 12.0

    else:
        warnings.append(
            "품질 기준을 통과한 주변 "
            "파라미터가 절반 미만입니다."
        )

    if robust_trial_percent >= 70.0:
        score += 20.0

        reasons.append(
            "중심값 성과의 70% 이상을 유지한 "
            "주변 조합이 충분합니다."
        )

    elif robust_trial_percent >= 50.0:
        score += 12.0

    else:
        warnings.append(
            "중심 파라미터와 비슷한 성과를 "
            "유지한 주변 조합이 적습니다."
        )

    if average_return > 0:
        score += 10.0

        reasons.append(
            "주변 파라미터의 평균 수익률이 "
            "플러스입니다."
        )

    else:
        warnings.append(
            "주변 파라미터의 평균 수익률이 "
            "0% 이하입니다."
        )

    if median_return > 0:
        score += 10.0

        reasons.append(
            "주변 파라미터 수익률의 "
            "중앙값이 플러스입니다."
        )

    if average_sharpe >= 1.0:
        score += 10.0

        reasons.append(
            "주변 파라미터의 평균 Sharpe가 "
            "1.0 이상입니다."
        )

    elif average_sharpe >= 0.50:
        score += 5.0

    else:
        warnings.append(
            "주변 파라미터의 평균 Sharpe가 "
            "0.5 미만입니다."
        )

    if abs(
        worst_drawdown
    ) <= 10.0:
        score += 10.0

        reasons.append(
            "주변 파라미터의 최악 낙폭이 "
            "10% 이내입니다."
        )

    elif abs(
        worst_drawdown
    ) > 20.0:
        warnings.append(
            "일부 주변 파라미터의 낙폭이 "
            "20%를 초과합니다."
        )

    if center_return != 0:
        performance_difference = abs(
            center_return
            - nearby_average_return
        )

        difference_ratio = (
            performance_difference
            / abs(
                center_return
            )
        ) * 100.0

        if difference_ratio <= 20.0:
            score += 10.0

            reasons.append(
                "중심 파라미터와 주변 파라미터의 "
                "평균 성과 차이가 작습니다."
            )

        elif difference_ratio >= 50.0:
            warnings.append(
                "중심 파라미터만 유난히 높아 "
                "봉우리 형태의 과최적화 가능성이 있습니다."
            )

    score = round(
        min(
            score,
            100.0,
        ),
        2,
    )

    overfitting_warning = (
        profitable_percent < 50.0
        or acceptable_percent < 50.0
        or robust_trial_percent < 50.0
        or average_return <= 0
    )

    if score >= 80.0:
        status = "ROBUST"

    elif score >= 60.0:
        status = "ACCEPTABLE"

    elif score >= 40.0:
        status = "WEAK"

    else:
        status = "OVERFIT_RISK"

    return (
        status,
        overfitting_warning,
        score,
        reasons,
        warnings,
    )


def run_parameter_robustness_test(
    symbol: str,
    period: str = "10y",
    interval: str = "1d",

    training_ratio: float = 0.70,

    initial_cash: float = 10_000.0,
    commission_per_trade: float = 0.0,

    center_entry_score: float = 64.0,
    center_exit_score: float = 42.0,

    center_stop_atr_multiple: float = 1.50,
    center_target_atr_multiple: float = 2.50,

    center_maximum_holding_days: int = 20,
    center_position_percent: float = 20.0,

    entry_scores: list[float] | None = None,
    exit_scores: list[float] | None = None,

    stop_atr_multiples: list[float] | None = None,
    target_atr_multiples: list[float] | None = None,

    maximum_holding_days_list: list[int] | None = None,
    position_percents: list[float] | None = None,

    minimum_validation_trades: int = 10,

    robust_return_ratio: float = 0.70,
    robust_sharpe_ratio: float = 0.70,
) -> ParameterRobustnessResult:
    """
    중심 파라미터와 주변 파라미터를
    Out-of-Sample 검증 구간에서 비교합니다.

    훈련 구간은 파라미터 결과 계산에
    사용하지 않습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if entry_scores is None:
        entry_scores = [
            62.0,
            64.0,
            66.0,
        ]

    if exit_scores is None:
        exit_scores = [
            40.0,
            42.0,
            44.0,
        ]

    if stop_atr_multiples is None:
        stop_atr_multiples = [
            center_stop_atr_multiple
        ]

    if target_atr_multiples is None:
        target_atr_multiples = [
            2.25,
            2.50,
            2.75,
        ]

    if maximum_holding_days_list is None:
        maximum_holding_days_list = [
            center_maximum_holding_days
        ]

    if position_percents is None:
        position_percents = [
            center_position_percent
        ]

    started_at = datetime.now()

    print()
    print("=" * 108)
    print(
        f"{normalized_symbol} V7.5 "
        "PARAMETER ROBUSTNESS TEST"
    )
    print("=" * 108)

    print(
        "Downloading full market data..."
    )

    full_data = get_history(
        symbol=normalized_symbol,
        period=period,
        interval=interval,
    )

    full_data = clean_market_data(
        full_data
    )

    (
        training_data,
        validation_data,
    ) = split_train_validation_data(
        data=full_data,
        training_ratio=training_ratio,
    )

    combinations = list(
        product(
            entry_scores,
            exit_scores,
            stop_atr_multiples,
            target_atr_multiples,
            maximum_holding_days_list,
            position_percents,
        )
    )

    print(
        f"Full period          : "
        f"{format_date(full_data.index[0])} "
        f"to {format_date(full_data.index[-1])}"
    )

    print(
        f"Validation period    : "
        f"{format_date(validation_data.index[0])} "
        f"to {format_date(validation_data.index[-1])}"
    )

    print(
        f"Training rows        : "
        f"{len(training_data)}"
    )

    print(
        f"Validation rows      : "
        f"{len(validation_data)}"
    )

    print(
        f"Total combinations   : "
        f"{len(combinations)}"
    )

    print("=" * 108)

    trials: list[
        ParameterTrialResult
    ] = []

    for trial_number, combination in enumerate(
        combinations,
        start=1,
    ):
        (
            entry_score,
            exit_score,
            stop_atr_multiple,
            target_atr_multiple,
            maximum_holding_days,
            position_percent,
        ) = combination

        distance_from_center = (
            calculate_parameter_distance(
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

                center_entry_score=(
                    center_entry_score
                ),

                center_exit_score=(
                    center_exit_score
                ),

                center_stop_atr_multiple=(
                    center_stop_atr_multiple
                ),

                center_target_atr_multiple=(
                    center_target_atr_multiple
                ),

                center_maximum_holding_days=(
                    center_maximum_holding_days
                ),
            )
        )

        try:
            backtest_result = (
                run_backtest_with_dataframe(
                    symbol=normalized_symbol,

                    data=validation_data,

                    initial_cash=initial_cash,

                    position_percent=(
                        position_percent
                    ),

                    entry_score=(
                        entry_score
                    ),

                    exit_score=(
                        exit_score
                    ),

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

                    dataset_name=(
                        f"PARAMETER_ROBUSTNESS_"
                        f"{trial_number}"
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

            robustness_score = (
                calculate_trial_score(
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
                        minimum_validation_trades
                    ),
                )
            )

            acceptable = (
                is_trial_acceptable(
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
                        minimum_validation_trades
                    ),
                )
            )

            trial = ParameterTrialResult(
                trial_number=trial_number,

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

                success=True,

                strategy_return_percent=(
                    strategy_return
                ),

                buy_hold_return_percent=(
                    buy_hold_return
                ),

                excess_return_percent=round(
                    strategy_return
                    - buy_hold_return,
                    2,
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

                robustness_score=(
                    robustness_score
                ),

                distance_from_center=(
                    distance_from_center
                ),

                profitable=(
                    strategy_return > 0
                ),

                acceptable=acceptable,
            )

            trials.append(
                trial
            )

            print(
                f"[{trial_number:>3}/{len(combinations)}] "
                f"Entry {entry_score:>5.1f} | "
                f"Exit {exit_score:>5.1f} | "
                f"Target {target_atr_multiple:>4.2f} | "
                f"Return {strategy_return:>7.2f}% | "
                f"Sharpe {sharpe_ratio:>5.2f} | "
                f"DD {maximum_drawdown:>7.2f}% | "
                f"Score {robustness_score:>6.2f}"
            )

        except Exception as error:
            failed_trial = build_failed_trial(
                trial_number=trial_number,

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

                distance_from_center=(
                    distance_from_center
                ),

                error=error,
            )

            trials.append(
                failed_trial
            )

            print(
                f"[{trial_number:>3}/{len(combinations)}] "
                f"FAILED: "
                f"{type(error).__name__} - "
                f"{error}"
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

    if not successful_trials:
        raise RuntimeError(
            "성공적으로 완료된 파라미터 "
            "테스트가 없습니다."
        )

    successful_trials.sort(
        key=lambda trial: (
            trial.robustness_score,
            trial.sharpe_ratio,
            trial.strategy_return_percent,
        ),
        reverse=True,
    )

    best_trial = (
        successful_trials[0]
    )

    center_trial = next(
        (
            trial
            for trial in successful_trials
            if (
                trial.entry_score
                == center_entry_score
                and trial.exit_score
                == center_exit_score
                and trial.stop_atr_multiple
                == center_stop_atr_multiple
                and trial.target_atr_multiple
                == center_target_atr_multiple
                and trial.maximum_holding_days
                == center_maximum_holding_days
                and trial.position_percent
                == center_position_percent
            )
        ),
        None,
    )

    if center_trial is None:
        raise RuntimeError(
            "중심 파라미터 조합이 테스트 목록에 없습니다."
        )

    nearby_trials = [
        trial
        for trial in successful_trials
        if trial.distance_from_center > 0
    ]

    profitable_trials = [
        trial
        for trial in successful_trials
        if trial.profitable
    ]

    acceptable_trials = [
        trial
        for trial in successful_trials
        if trial.acceptable
    ]

    center_return = (
        center_trial
        .strategy_return_percent
    )

    center_sharpe = (
        center_trial
        .sharpe_ratio
    )

    return_threshold = (
        center_return
        * robust_return_ratio
    )

    sharpe_threshold = (
        center_sharpe
        * robust_sharpe_ratio
    )

    robust_trials = [
        trial
        for trial in nearby_trials
        if (
            trial.strategy_return_percent
            >= return_threshold
            and trial.sharpe_ratio
            >= sharpe_threshold
        )
    ]

    successful_count = len(
        successful_trials
    )

    profitable_percent = round(
        len(
            profitable_trials
        )
        / successful_count
        * 100.0,
        2,
    )

    acceptable_percent = round(
        len(
            acceptable_trials
        )
        / successful_count
        * 100.0,
        2,
    )

    robust_trial_percent = (
        round(
            len(
                robust_trials
            )
            / len(
                nearby_trials
            )
            * 100.0,
            2,
        )
        if nearby_trials
        else 0.0
    )

    returns = [
        trial.strategy_return_percent
        for trial in successful_trials
    ]

    sharpes = [
        trial.sharpe_ratio
        for trial in successful_trials
    ]

    drawdowns = [
        trial.maximum_drawdown_percent
        for trial in successful_trials
    ]

    profit_factors = [
        trial.profit_factor
        for trial in successful_trials
    ]

    win_rates = [
        trial.win_rate_percent
        for trial in successful_trials
    ]

    nearby_returns = [
        trial.strategy_return_percent
        for trial in nearby_trials
    ]

    nearby_sharpes = [
        trial.sharpe_ratio
        for trial in nearby_trials
    ]

    average_return = safe_average(
        returns
    )

    median_return = safe_median(
        returns
    )

    average_sharpe = safe_average(
        sharpes
    )

    worst_drawdown = round(
        min(
            drawdowns
        ),
        2,
    )

    nearby_average_return = (
        safe_average(
            nearby_returns
        )
    )

    nearby_average_sharpe = (
        safe_average(
            nearby_sharpes
        )
    )

    (
        validation_status,
        overfitting_warning,
        robustness_score,
        reasons,
        warnings,
    ) = evaluate_overall_robustness(
        successful_trials=(
            successful_trials
        ),

        profitable_percent=(
            profitable_percent
        ),

        acceptable_percent=(
            acceptable_percent
        ),

        robust_trial_percent=(
            robust_trial_percent
        ),

        average_return=(
            average_return
        ),

        median_return=(
            median_return
        ),

        average_sharpe=(
            average_sharpe
        ),

        worst_drawdown=(
            worst_drawdown
        ),

        center_return=(
            center_return
        ),

        nearby_average_return=(
            nearby_average_return
        ),
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return ParameterRobustnessResult(
        version="V7.5",

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

        validation_start_date=format_date(
            validation_data.index[0]
        ),

        validation_end_date=format_date(
            validation_data.index[-1]
        ),

        full_rows=len(
            full_data
        ),

        training_rows=len(
            training_data
        ),

        validation_rows=len(
            validation_data
        ),

        training_ratio_percent=round(
            training_ratio
            * 100.0,
            2,
        ),

        validation_ratio_percent=round(
            (
                1.0
                - training_ratio
            )
            * 100.0,
            2,
        ),

        center_parameters={
            "entry_score": (
                center_entry_score
            ),

            "exit_score": (
                center_exit_score
            ),

            "stop_atr_multiple": (
                center_stop_atr_multiple
            ),

            "target_atr_multiple": (
                center_target_atr_multiple
            ),

            "maximum_holding_days": (
                center_maximum_holding_days
            ),

            "position_percent": (
                center_position_percent
            ),
        },

        total_trials=len(
            trials
        ),

        successful_trials=len(
            successful_trials
        ),

        failed_trials=len(
            failed_trials
        ),

        profitable_trials=len(
            profitable_trials
        ),

        acceptable_trials=len(
            acceptable_trials
        ),

        profitable_percent=(
            profitable_percent
        ),

        acceptable_percent=(
            acceptable_percent
        ),

        average_return_percent=(
            average_return
        ),

        median_return_percent=(
            median_return
        ),

        average_sharpe_ratio=(
            average_sharpe
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
            worst_drawdown
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

        best_trial=(
            best_trial.to_dict()
        ),

        center_trial=(
            center_trial.to_dict()
        ),

        center_return_percent=(
            center_return
        ),

        center_sharpe_ratio=(
            center_sharpe
        ),

        center_drawdown_percent=(
            center_trial
            .maximum_drawdown_percent
        ),

        nearby_average_return_percent=(
            nearby_average_return
        ),

        nearby_average_sharpe_ratio=(
            nearby_average_sharpe
        ),

        center_vs_nearby_return_difference=round(
            center_return
            - nearby_average_return,
            2,
        ),

        center_vs_nearby_sharpe_difference=round(
            center_sharpe
            - nearby_average_sharpe,
            2,
        ),

        robust_trial_percent=(
            robust_trial_percent
        ),

        parameter_robustness_score=(
            robustness_score
        ),

        validation_status=(
            validation_status
        ),

        overfitting_warning=(
            overfitting_warning
        ),

        reasons=reasons,
        warnings=warnings,

        trials=[
            trial.to_dict()
            for trial in successful_trials
        ]
        + [
            trial.to_dict()
            for trial in failed_trials
        ],
    )


def save_parameter_robustness_result(
    result: ParameterRobustnessResult,
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
            f"{result.symbol}_parameter_robustness_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_parameter_robustness_"
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


def print_parameter_robustness_result(
    result: ParameterRobustnessResult,
) -> None:
    """
    전체 강건성 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 126)
    print(
        f"{result.symbol} V7.5 "
        "PARAMETER ROBUSTNESS RESULT"
    )
    print("=" * 126)

    print(
        f"Validation period        : "
        f"{result.validation_start_date} "
        f"to {result.validation_end_date}"
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
        f"Robustness score         : "
        f"{result.parameter_robustness_score:.2f}/100"
    )

    print()
    print("TRIAL CONSISTENCY")
    print("-" * 126)

    print(
        f"Total trials             : "
        f"{result.total_trials}"
    )

    print(
        f"Successful trials        : "
        f"{result.successful_trials}"
    )

    print(
        f"Failed trials            : "
        f"{result.failed_trials}"
    )

    print(
        f"Profitable trials        : "
        f"{result.profitable_trials}/"
        f"{result.successful_trials} "
        f"({result.profitable_percent:.2f}%)"
    )

    print(
        f"Acceptable trials        : "
        f"{result.acceptable_trials}/"
        f"{result.successful_trials} "
        f"({result.acceptable_percent:.2f}%)"
    )

    print(
        f"Robust nearby trials     : "
        f"{result.robust_trial_percent:.2f}%"
    )

    print()
    print("AVERAGE PERFORMANCE")
    print("-" * 126)

    print(
        f"Average return           : "
        f"{result.average_return_percent:.2f}%"
    )

    print(
        f"Median return            : "
        f"{result.median_return_percent:.2f}%"
    )

    print(
        f"Average Sharpe           : "
        f"{result.average_sharpe_ratio:.2f}"
    )

    print(
        f"Median Sharpe            : "
        f"{result.median_sharpe_ratio:.2f}"
    )

    print(
        f"Average drawdown         : "
        f"{result.average_drawdown_percent:.2f}%"
    )

    print(
        f"Worst drawdown           : "
        f"{result.worst_drawdown_percent:.2f}%"
    )

    print(
        f"Average profit factor    : "
        f"{result.average_profit_factor:.2f}"
    )

    print(
        f"Average win rate         : "
        f"{result.average_win_rate_percent:.2f}%"
    )

    print()
    print("CENTER PARAMETER PERFORMANCE")
    print("-" * 126)

    center = result.center_parameters

    print(
        f"Center parameters        : "
        f"Entry {center['entry_score']}, "
        f"Exit {center['exit_score']}, "
        f"Stop {center['stop_atr_multiple']}, "
        f"Target {center['target_atr_multiple']}, "
        f"Hold {center['maximum_holding_days']}"
    )

    print(
        f"Center return            : "
        f"{result.center_return_percent:.2f}%"
    )

    print(
        f"Center Sharpe            : "
        f"{result.center_sharpe_ratio:.2f}"
    )

    print(
        f"Center drawdown          : "
        f"{result.center_drawdown_percent:.2f}%"
    )

    print(
        f"Nearby average return    : "
        f"{result.nearby_average_return_percent:.2f}%"
    )

    print(
        f"Nearby average Sharpe    : "
        f"{result.nearby_average_sharpe_ratio:.2f}"
    )

    print(
        f"Center return difference : "
        f"{result.center_vs_nearby_return_difference:+.2f}%p"
    )

    print(
        f"Center Sharpe difference : "
        f"{result.center_vs_nearby_sharpe_difference:+.2f}"
    )

    print()
    print("TOP PARAMETER COMBINATIONS")
    print("-" * 126)

    print(
        f"{'Rank':<6}"
        f"{'Entry':>8}"
        f"{'Exit':>8}"
        f"{'Target':>10}"
        f"{'Hold':>8}"
        f"{'Return':>11}"
        f"{'Sharpe':>10}"
        f"{'Drawdown':>11}"
        f"{'PF':>8}"
        f"{'Trades':>9}"
        f"{'Score':>10}"
    )

    print("-" * 126)

    successful = [
        trial
        for trial in result.trials
        if trial[
            "success"
        ]
    ]

    for rank, trial in enumerate(
        successful[:10],
        start=1,
    ):
        print(
            f"{rank:<6}"
            f"{trial['entry_score']:>8.0f}"
            f"{trial['exit_score']:>8.0f}"
            f"{trial['target_atr_multiple']:>10.2f}"
            f"{trial['maximum_holding_days']:>8}"
            f"{trial['strategy_return_percent']:>10.2f}%"
            f"{trial['sharpe_ratio']:>10.2f}"
            f"{trial['maximum_drawdown_percent']:>10.2f}%"
            f"{trial['profit_factor']:>8.2f}"
            f"{trial['total_trades']:>9}"
            f"{trial['robustness_score']:>10.2f}"
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

    print("=" * 126)

    print(
        "주의: 주변 파라미터 검사는 전략의 "
        "민감도를 확인하는 도구이며 미래 수익을 "
        "보장하지 않습니다."
    )