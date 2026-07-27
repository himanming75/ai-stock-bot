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
    run_optimizer_with_dataframe,
    safe_float,
)
from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "walk_forward"
)


@dataclass
class WalkForwardWindowResult:
    """
    Walk-Forward 검증의 한 구간 결과입니다.
    """

    window_number: int

    training_start_date: str
    training_end_date: str

    validation_start_date: str
    validation_end_date: str

    training_rows: int
    validation_rows: int

    optimization_success: bool
    validation_success: bool

    entry_score: float
    exit_score: float

    stop_atr_multiple: float
    target_atr_multiple: float

    maximum_holding_days: int
    position_percent: float

    training_optimization_score: float
    training_return_percent: float
    training_sharpe_ratio: float
    training_drawdown_percent: float
    training_profit_factor: float
    training_total_trades: int

    validation_return_percent: float
    validation_buy_hold_return_percent: float
    validation_excess_return_percent: float

    validation_sharpe_ratio: float
    validation_drawdown_percent: float
    validation_profit_factor: float
    validation_win_rate_percent: float
    validation_total_trades: int

    default_return_percent: float
    default_sharpe_ratio: float
    default_drawdown_percent: float

    beat_default_return: bool
    beat_default_sharpe: bool

    profitable: bool
    acceptable: bool

    return_retention_percent: float
    sharpe_retention_percent: float

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WalkForwardValidationResult:
    """
    전체 Walk-Forward 검증 결과입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    full_start_date: str
    full_end_date: str
    total_rows: int

    training_window_rows: int
    validation_window_rows: int
    step_rows: int

    estimated_trading_days_per_year: int

    total_windows: int
    successful_windows: int
    failed_windows: int

    profitable_windows: int
    acceptable_windows: int

    beat_default_return_windows: int
    beat_default_sharpe_windows: int

    profitable_window_percent: float
    acceptable_window_percent: float

    beat_default_return_percent: float
    beat_default_sharpe_percent: float

    average_validation_return_percent: float
    median_validation_return_percent: float

    average_default_return_percent: float

    average_excess_return_percent: float
    median_excess_return_percent: float

    average_validation_sharpe_ratio: float
    average_default_sharpe_ratio: float

    average_validation_drawdown_percent: float
    worst_validation_drawdown_percent: float

    average_profit_factor: float
    average_win_rate_percent: float
    total_validation_trades: int

    average_return_retention_percent: float
    average_sharpe_retention_percent: float

    parameter_stability_score: float

    most_common_entry_score: float | None
    most_common_exit_score: float | None

    most_common_stop_atr: float | None
    most_common_target_atr: float | None

    most_common_holding_days: int | None

    validation_status: str
    overfitting_warning: bool

    reasons: list[str]
    warnings: list[str]

    windows: list[dict[str, Any]]

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


def calculate_retention_percent(
    training_value: float,
    validation_value: float,
) -> float:
    """
    훈련 성과 중 검증 구간에서 유지된 비율입니다.
    """

    training_value = safe_float(
        training_value
    )

    validation_value = safe_float(
        validation_value
    )

    if training_value <= 0:
        return 0.0

    return round(
        (
            validation_value
            / training_value
        )
        * 100.0,
        2,
    )


def safe_average(
    values: list[float],
) -> float:
    """
    값 목록의 평균을 안전하게 계산합니다.
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
    값 목록의 중앙값을 계산합니다.
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


def get_most_common_value(
    values: list[Any],
) -> Any | None:
    """
    가장 자주 선택된 값을 반환합니다.
    """

    if not values:
        return None

    series = pd.Series(
        values
    )

    modes = series.mode()

    if modes.empty:
        return None

    return modes.iloc[0]


def calculate_parameter_stability_score(
    windows: list[WalkForwardWindowResult],
) -> float:
    """
    구간마다 같은 파라미터가 얼마나 자주
    선택되는지 0~100점으로 계산합니다.

    100점에 가까울수록 파라미터가 안정적입니다.
    """

    successful = [
        window
        for window in windows
        if (
            window.optimization_success
            and window.validation_success
        )
    ]

    if not successful:
        return 0.0

    parameter_groups = [
        [
            window.entry_score
            for window in successful
        ],
        [
            window.exit_score
            for window in successful
        ],
        [
            window.stop_atr_multiple
            for window in successful
        ],
        [
            window.target_atr_multiple
            for window in successful
        ],
        [
            window.maximum_holding_days
            for window in successful
        ],
    ]

    stability_scores: list[float] = []

    for values in parameter_groups:
        most_common = get_most_common_value(
            values
        )

        if most_common is None:
            stability_scores.append(
                0.0
            )
            continue

        matching_count = sum(
            1
            for value in values
            if value == most_common
        )

        stability_scores.append(
            (
                matching_count
                / len(values)
            )
            * 100.0
        )

    return round(
        sum(stability_scores)
        / len(stability_scores),
        2,
    )


def create_walk_forward_ranges(
    total_rows: int,
    training_window_rows: int,
    validation_window_rows: int,
    step_rows: int,
) -> list[
    tuple[
        int,
        int,
        int,
        int,
    ]
]:
    """
    Walk-Forward 훈련 및 검증 구간 위치를 만듭니다.

    반환값:

    (
        training_start,
        training_end,
        validation_start,
        validation_end,
    )
    """

    if training_window_rows < 200:
        raise ValueError(
            "training_window_rows는 "
            "최소 200 이상이어야 합니다."
        )

    if validation_window_rows < 20:
        raise ValueError(
            "validation_window_rows는 "
            "최소 20 이상이어야 합니다."
        )

    if step_rows < 1:
        raise ValueError(
            "step_rows는 1 이상이어야 합니다."
        )

    minimum_required_rows = (
        training_window_rows
        + validation_window_rows
    )

    if total_rows < minimum_required_rows:
        raise ValueError(
            "시장 데이터가 Walk-Forward 검증에 "
            "충분하지 않습니다. "
            f"필요 행 수: {minimum_required_rows}, "
            f"현재 행 수: {total_rows}"
        )

    ranges = []

    training_start = 0

    while True:
        training_end = (
            training_start
            + training_window_rows
        )

        validation_start = (
            training_end
        )

        validation_end = (
            validation_start
            + validation_window_rows
        )

        if validation_end > total_rows:
            break

        ranges.append(
            (
                training_start,
                training_end,
                validation_start,
                validation_end,
            )
        )

        training_start += step_rows

    return ranges


def build_failed_window(
    window_number: int,
    training_data: pd.DataFrame,
    validation_data: pd.DataFrame,
    error: Exception,
) -> WalkForwardWindowResult:
    """
    실패한 구간 결과를 생성합니다.
    """

    return WalkForwardWindowResult(
        window_number=window_number,

        training_start_date=format_date(
            training_data.index[0]
        ),

        training_end_date=format_date(
            training_data.index[-1]
        ),

        validation_start_date=format_date(
            validation_data.index[0]
        ),

        validation_end_date=format_date(
            validation_data.index[-1]
        ),

        training_rows=len(
            training_data
        ),

        validation_rows=len(
            validation_data
        ),

        optimization_success=False,
        validation_success=False,

        entry_score=0.0,
        exit_score=0.0,

        stop_atr_multiple=0.0,
        target_atr_multiple=0.0,

        maximum_holding_days=0,
        position_percent=0.0,

        training_optimization_score=0.0,
        training_return_percent=0.0,
        training_sharpe_ratio=0.0,
        training_drawdown_percent=0.0,
        training_profit_factor=0.0,
        training_total_trades=0,

        validation_return_percent=0.0,
        validation_buy_hold_return_percent=0.0,
        validation_excess_return_percent=0.0,

        validation_sharpe_ratio=0.0,
        validation_drawdown_percent=0.0,
        validation_profit_factor=0.0,
        validation_win_rate_percent=0.0,
        validation_total_trades=0,

        default_return_percent=0.0,
        default_sharpe_ratio=0.0,
        default_drawdown_percent=0.0,

        beat_default_return=False,
        beat_default_sharpe=False,

        profitable=False,
        acceptable=False,

        return_retention_percent=0.0,
        sharpe_retention_percent=0.0,

        error_type=type(
            error
        ).__name__,

        error_message=str(
            error
        ),
    )


def evaluate_window_acceptability(
    validation_return: float,
    validation_sharpe: float,
    validation_drawdown: float,
    validation_profit_factor: float,
    validation_trades: int,
    minimum_validation_trades: int,
) -> bool:
    """
    한 검증 구간이 최소 품질 조건을
    충족하는지 판단합니다.
    """

    return (
        validation_return > 0
        and validation_sharpe >= 0.50
        and abs(
            validation_drawdown
        ) <= 15.0
        and validation_profit_factor >= 1.10
        and validation_trades
        >= minimum_validation_trades
    )


def evaluate_overall_quality(
    successful_windows: list[
        WalkForwardWindowResult
    ],
    profitable_percent: float,
    acceptable_percent: float,
    beat_default_return_percent: float,
    average_validation_return: float,
    average_validation_sharpe: float,
    average_validation_drawdown: float,
    average_return_retention: float,
    parameter_stability_score: float,
) -> tuple[
    str,
    bool,
    list[str],
    list[str],
]:
    """
    전체 Walk-Forward 결과를 평가합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if not successful_windows:
        return (
            "FAILED",
            True,
            [],
            [
                "성공적으로 완료된 검증 구간이 없습니다."
            ],
        )

    score = 0

    if profitable_percent >= 70.0:
        score += 3

        reasons.append(
            "70% 이상의 검증 구간에서 "
            "플러스 수익을 기록했습니다."
        )

    elif profitable_percent >= 50.0:
        score += 2

        reasons.append(
            "과반수의 검증 구간에서 "
            "플러스 수익을 기록했습니다."
        )

    else:
        warnings.append(
            "수익을 기록한 검증 구간이 "
            "절반 미만입니다."
        )

    if acceptable_percent >= 70.0:
        score += 3

        reasons.append(
            "대부분의 검증 구간이 "
            "최소 품질 기준을 통과했습니다."
        )

    elif acceptable_percent >= 50.0:
        score += 2

    else:
        warnings.append(
            "품질 기준을 통과한 검증 구간이 "
            "절반 미만입니다."
        )

    if beat_default_return_percent >= 60.0:
        score += 2

        reasons.append(
            "최적화 전략이 다수의 구간에서 "
            "기본 전략보다 높은 수익률을 기록했습니다."
        )

    elif beat_default_return_percent < 40.0:
        warnings.append(
            "최적화 전략이 기본 전략보다 "
            "우수했던 구간이 적습니다."
        )

    if average_validation_return > 0:
        score += 1

        reasons.append(
            "평균 검증 수익률이 플러스입니다."
        )

    else:
        warnings.append(
            "평균 검증 수익률이 "
            "0% 이하입니다."
        )

    if average_validation_sharpe >= 1.0:
        score += 2

        reasons.append(
            "평균 검증 Sharpe Ratio가 "
            "1.0 이상입니다."
        )

    elif average_validation_sharpe >= 0.50:
        score += 1

    else:
        warnings.append(
            "평균 검증 Sharpe Ratio가 "
            "0.5 미만입니다."
        )

    if abs(
        average_validation_drawdown
    ) <= 10.0:
        score += 1

        reasons.append(
            "평균 검증 최대 낙폭이 "
            "10% 이내입니다."
        )

    else:
        warnings.append(
            "평균 검증 최대 낙폭이 "
            "10%를 초과합니다."
        )

    if average_return_retention >= 40.0:
        score += 2

        reasons.append(
            "훈련 수익률 대비 평균 검증 수익률 "
            "유지율이 40% 이상입니다."
        )

    elif average_return_retention < 20.0:
        warnings.append(
            "훈련 성과 대비 검증 성과 "
            "유지율이 매우 낮습니다."
        )

    if parameter_stability_score >= 70.0:
        score += 2

        reasons.append(
            "검증 구간마다 선택되는 "
            "파라미터가 비교적 안정적입니다."
        )

    elif parameter_stability_score < 40.0:
        warnings.append(
            "구간마다 선택되는 파라미터가 "
            "크게 달라 전략 안정성이 낮을 수 있습니다."
        )

    overfitting_warning = (
        profitable_percent < 50.0
        or acceptable_percent < 50.0
        or beat_default_return_percent < 40.0
        or average_return_retention < 20.0
        or parameter_stability_score < 40.0
    )

    if score >= 13:
        status = "ROBUST"

    elif score >= 9:
        status = "ACCEPTABLE"

    elif score >= 6:
        status = "WEAK"

    else:
        status = "OVERFIT_RISK"

    return (
        status,
        overfitting_warning,
        reasons,
        warnings,
    )


def run_walk_forward_validation(
    symbol: str,
    period: str = "10y",
    interval: str = "1d",

    training_years: float = 4.0,
    validation_years: float = 1.0,
    step_years: float = 1.0,

    estimated_trading_days_per_year: int = 252,

    initial_cash: float = 10_000.0,
    commission_per_trade: float = 0.0,

    entry_scores: list[float] | None = None,
    exit_scores: list[float] | None = None,

    stop_atr_multiples: list[float] | None = None,
    target_atr_multiples: list[float] | None = None,

    maximum_holding_days_list: list[int] | None = None,
    position_percents: list[float] | None = None,

    minimum_training_trades: int = 30,
    minimum_validation_trades: int = 10,

    top_n: int = 5,
) -> WalkForwardValidationResult:
    """
    여러 개의 시간 구간을 이동하면서
    반복적으로 최적화 및 검증합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if entry_scores is None:
        entry_scores = [
            64.0,
            68.0,
        ]

    if exit_scores is None:
        exit_scores = [
            38.0,
            42.0,
        ]

    if stop_atr_multiples is None:
        stop_atr_multiples = [
            1.25,
            1.50,
        ]

    if target_atr_multiples is None:
        target_atr_multiples = [
            2.50,
            3.00,
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

    training_window_rows = int(
        training_years
        * estimated_trading_days_per_year
    )

    validation_window_rows = int(
        validation_years
        * estimated_trading_days_per_year
    )

    step_rows = int(
        step_years
        * estimated_trading_days_per_year
    )

    started_at = datetime.now()

    print()
    print("=" * 104)
    print(
        f"{normalized_symbol} V7.4 "
        "WALK-FORWARD VALIDATION"
    )
    print("=" * 104)

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

    ranges = create_walk_forward_ranges(
        total_rows=len(
            full_data
        ),

        training_window_rows=(
            training_window_rows
        ),

        validation_window_rows=(
            validation_window_rows
        ),

        step_rows=step_rows,
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
        f"Training window      : "
        f"{training_window_rows} rows "
        f"(approximately {training_years:.1f} years)"
    )

    print(
        f"Validation window    : "
        f"{validation_window_rows} rows "
        f"(approximately {validation_years:.1f} years)"
    )

    print(
        f"Step size            : "
        f"{step_rows} rows "
        f"(approximately {step_years:.1f} years)"
    )

    print(
        f"Total windows        : "
        f"{len(ranges)}"
    )

    print("=" * 104)

    windows: list[
        WalkForwardWindowResult
    ] = []

    for window_number, range_values in enumerate(
        ranges,
        start=1,
    ):
        (
            training_start,
            training_end,
            validation_start,
            validation_end,
        ) = range_values

        training_data = (
            full_data.iloc[
                training_start:
                training_end
            ]
            .copy()
        )

        validation_data = (
            full_data.iloc[
                validation_start:
                validation_end
            ]
            .copy()
        )

        print()
        print("#" * 104)

        print(
            f"[WINDOW "
            f"{window_number}/{len(ranges)}]"
        )

        print("#" * 104)

        print(
            f"Training period      : "
            f"{format_date(training_data.index[0])} "
            f"to "
            f"{format_date(training_data.index[-1])}"
        )

        print(
            f"Validation period    : "
            f"{format_date(validation_data.index[0])} "
            f"to "
            f"{format_date(validation_data.index[-1])}"
        )

        try:
            optimizer_result = (
                run_optimizer_with_dataframe(
                    symbol=normalized_symbol,

                    training_data=training_data,

                    initial_cash=initial_cash,

                    commission_per_trade=(
                        commission_per_trade
                    ),

                    entry_scores=entry_scores,
                    exit_scores=exit_scores,

                    stop_atr_multiples=(
                        stop_atr_multiples
                    ),

                    target_atr_multiples=(
                        target_atr_multiples
                    ),

                    maximum_holding_days_list=(
                        maximum_holding_days_list
                    ),

                    position_percents=(
                        position_percents
                    ),

                    minimum_trades=(
                        minimum_training_trades
                    ),

                    top_n=top_n,
                )
            )

            best = (
                optimizer_result
                .best_trial
            )

            if best is None:
                raise RuntimeError(
                    "훈련 구간에서 최적 파라미터를 "
                    "찾지 못했습니다."
                )

            validation_result = (
                run_backtest_with_dataframe(
                    symbol=normalized_symbol,

                    data=validation_data,

                    initial_cash=initial_cash,

                    position_percent=safe_float(
                        best[
                            "position_percent"
                        ]
                    ),

                    entry_score=safe_float(
                        best[
                            "entry_score"
                        ]
                    ),

                    exit_score=safe_float(
                        best[
                            "exit_score"
                        ]
                    ),

                    stop_atr_multiple=safe_float(
                        best[
                            "stop_atr_multiple"
                        ]
                    ),

                    target_atr_multiple=safe_float(
                        best[
                            "target_atr_multiple"
                        ]
                    ),

                    maximum_holding_days=int(
                        best[
                            "maximum_holding_days"
                        ]
                    ),

                    commission_per_trade=(
                        commission_per_trade
                    ),

                    dataset_name=(
                        f"WALK_FORWARD_"
                        f"WINDOW_{window_number}"
                    ),
                )
            )

            default_result = (
                run_backtest_with_dataframe(
                    symbol=normalized_symbol,

                    data=validation_data,

                    initial_cash=initial_cash,

                    position_percent=20.0,

                    entry_score=68.0,
                    exit_score=42.0,

                    stop_atr_multiple=1.50,
                    target_atr_multiple=3.00,

                    maximum_holding_days=20,

                    commission_per_trade=(
                        commission_per_trade
                    ),

                    dataset_name=(
                        f"WALK_FORWARD_DEFAULT_"
                        f"{window_number}"
                    ),
                )
            )

            if not validation_result.success:
                raise RuntimeError(
                    validation_result.error_message
                    or "검증 백테스트에 실패했습니다."
                )

            training_return = safe_float(
                best[
                    "strategy_return_percent"
                ]
            )

            training_sharpe = safe_float(
                best[
                    "sharpe_ratio"
                ]
            )

            validation_return = safe_float(
                validation_result
                .total_return_percent
            )

            validation_buy_hold = safe_float(
                validation_result
                .buy_hold_return_percent
            )

            validation_sharpe = safe_float(
                validation_result
                .sharpe_ratio
            )

            validation_drawdown = safe_float(
                validation_result
                .maximum_drawdown_percent
            )

            validation_profit_factor = safe_float(
                validation_result
                .profit_factor
            )

            validation_total_trades = int(
                validation_result
                .total_trades
            )

            default_return = safe_float(
                default_result
                .total_return_percent
            )

            default_sharpe = safe_float(
                default_result
                .sharpe_ratio
            )

            acceptable = (
                evaluate_window_acceptability(
                    validation_return=(
                        validation_return
                    ),

                    validation_sharpe=(
                        validation_sharpe
                    ),

                    validation_drawdown=(
                        validation_drawdown
                    ),

                    validation_profit_factor=(
                        validation_profit_factor
                    ),

                    validation_trades=(
                        validation_total_trades
                    ),

                    minimum_validation_trades=(
                        minimum_validation_trades
                    ),
                )
            )

            window_result = (
                WalkForwardWindowResult(
                    window_number=window_number,

                    training_start_date=format_date(
                        training_data.index[0]
                    ),

                    training_end_date=format_date(
                        training_data.index[-1]
                    ),

                    validation_start_date=format_date(
                        validation_data.index[0]
                    ),

                    validation_end_date=format_date(
                        validation_data.index[-1]
                    ),

                    training_rows=len(
                        training_data
                    ),

                    validation_rows=len(
                        validation_data
                    ),

                    optimization_success=True,
                    validation_success=True,

                    entry_score=safe_float(
                        best[
                            "entry_score"
                        ]
                    ),

                    exit_score=safe_float(
                        best[
                            "exit_score"
                        ]
                    ),

                    stop_atr_multiple=safe_float(
                        best[
                            "stop_atr_multiple"
                        ]
                    ),

                    target_atr_multiple=safe_float(
                        best[
                            "target_atr_multiple"
                        ]
                    ),

                    maximum_holding_days=int(
                        best[
                            "maximum_holding_days"
                        ]
                    ),

                    position_percent=safe_float(
                        best[
                            "position_percent"
                        ]
                    ),

                    training_optimization_score=safe_float(
                        best[
                            "optimization_score"
                        ]
                    ),

                    training_return_percent=(
                        training_return
                    ),

                    training_sharpe_ratio=(
                        training_sharpe
                    ),

                    training_drawdown_percent=safe_float(
                        best[
                            "maximum_drawdown_percent"
                        ]
                    ),

                    training_profit_factor=safe_float(
                        best[
                            "profit_factor"
                        ]
                    ),

                    training_total_trades=int(
                        best[
                            "total_trades"
                        ]
                    ),

                    validation_return_percent=(
                        validation_return
                    ),

                    validation_buy_hold_return_percent=(
                        validation_buy_hold
                    ),

                    validation_excess_return_percent=round(
                        validation_return
                        - validation_buy_hold,
                        2,
                    ),

                    validation_sharpe_ratio=(
                        validation_sharpe
                    ),

                    validation_drawdown_percent=(
                        validation_drawdown
                    ),

                    validation_profit_factor=(
                        validation_profit_factor
                    ),

                    validation_win_rate_percent=safe_float(
                        validation_result
                        .win_rate_percent
                    ),

                    validation_total_trades=(
                        validation_total_trades
                    ),

                    default_return_percent=(
                        default_return
                    ),

                    default_sharpe_ratio=(
                        default_sharpe
                    ),

                    default_drawdown_percent=safe_float(
                        default_result
                        .maximum_drawdown_percent
                    ),

                    beat_default_return=(
                        validation_return
                        > default_return
                    ),

                    beat_default_sharpe=(
                        validation_sharpe
                        > default_sharpe
                    ),

                    profitable=(
                        validation_return
                        > 0
                    ),

                    acceptable=acceptable,

                    return_retention_percent=(
                        calculate_retention_percent(
                            training_value=(
                                training_return
                            ),

                            validation_value=(
                                validation_return
                            ),
                        )
                    ),

                    sharpe_retention_percent=(
                        calculate_retention_percent(
                            training_value=(
                                training_sharpe
                            ),

                            validation_value=(
                                validation_sharpe
                            ),
                        )
                    ),
                )
            )

            windows.append(
                window_result
            )

            print(
                f"Selected parameters  : "
                f"Entry {window_result.entry_score:.0f}, "
                f"Exit {window_result.exit_score:.0f}, "
                f"Stop {window_result.stop_atr_multiple:.2f}, "
                f"Target {window_result.target_atr_multiple:.2f}, "
                f"Hold {window_result.maximum_holding_days}"
            )

            print(
                f"Validation result    : "
                f"Return "
                f"{window_result.validation_return_percent:.2f}% | "
                f"Sharpe "
                f"{window_result.validation_sharpe_ratio:.2f} | "
                f"DD "
                f"{window_result.validation_drawdown_percent:.2f}% | "
                f"Trades "
                f"{window_result.validation_total_trades}"
            )

            print(
                f"Default result       : "
                f"Return "
                f"{window_result.default_return_percent:.2f}% | "
                f"Sharpe "
                f"{window_result.default_sharpe_ratio:.2f}"
            )

            print(
                f"Window status        : "
                f"{'ACCEPTABLE' if acceptable else 'WEAK'}"
            )

        except Exception as error:
            failed_window = build_failed_window(
                window_number=window_number,
                training_data=training_data,
                validation_data=validation_data,
                error=error,
            )

            windows.append(
                failed_window
            )

            print(
                f"Window failed        : "
                f"{type(error).__name__} - "
                f"{error}"
            )

    successful_windows = [
        window
        for window in windows
        if (
            window.optimization_success
            and window.validation_success
        )
    ]

    failed_windows = [
        window
        for window in windows
        if not (
            window.optimization_success
            and window.validation_success
        )
    ]

    profitable_windows = [
        window
        for window in successful_windows
        if window.profitable
    ]

    acceptable_windows = [
        window
        for window in successful_windows
        if window.acceptable
    ]

    beat_default_return_windows = [
        window
        for window in successful_windows
        if window.beat_default_return
    ]

    beat_default_sharpe_windows = [
        window
        for window in successful_windows
        if window.beat_default_sharpe
    ]

    successful_count = len(
        successful_windows
    )

    profitable_percent = (
        round(
            len(
                profitable_windows
            )
            / successful_count
            * 100.0,
            2,
        )
        if successful_count
        else 0.0
    )

    acceptable_percent = (
        round(
            len(
                acceptable_windows
            )
            / successful_count
            * 100.0,
            2,
        )
        if successful_count
        else 0.0
    )

    beat_default_return_percent = (
        round(
            len(
                beat_default_return_windows
            )
            / successful_count
            * 100.0,
            2,
        )
        if successful_count
        else 0.0
    )

    beat_default_sharpe_percent = (
        round(
            len(
                beat_default_sharpe_windows
            )
            / successful_count
            * 100.0,
            2,
        )
        if successful_count
        else 0.0
    )

    validation_returns = [
        window.validation_return_percent
        for window in successful_windows
    ]

    default_returns = [
        window.default_return_percent
        for window in successful_windows
    ]

    excess_returns = [
        window.validation_excess_return_percent
        for window in successful_windows
    ]

    validation_sharpes = [
        window.validation_sharpe_ratio
        for window in successful_windows
    ]

    default_sharpes = [
        window.default_sharpe_ratio
        for window in successful_windows
    ]

    validation_drawdowns = [
        window.validation_drawdown_percent
        for window in successful_windows
    ]

    profit_factors = [
        window.validation_profit_factor
        for window in successful_windows
    ]

    win_rates = [
        window.validation_win_rate_percent
        for window in successful_windows
    ]

    return_retentions = [
        window.return_retention_percent
        for window in successful_windows
    ]

    sharpe_retentions = [
        window.sharpe_retention_percent
        for window in successful_windows
    ]

    parameter_stability_score = (
        calculate_parameter_stability_score(
            successful_windows
        )
    )

    average_validation_return = (
        safe_average(
            validation_returns
        )
    )

    average_validation_sharpe = (
        safe_average(
            validation_sharpes
        )
    )

    average_validation_drawdown = (
        safe_average(
            validation_drawdowns
        )
    )

    average_return_retention = (
        safe_average(
            return_retentions
        )
    )

    (
        validation_status,
        overfitting_warning,
        reasons,
        warnings,
    ) = evaluate_overall_quality(
        successful_windows=(
            successful_windows
        ),

        profitable_percent=(
            profitable_percent
        ),

        acceptable_percent=(
            acceptable_percent
        ),

        beat_default_return_percent=(
            beat_default_return_percent
        ),

        average_validation_return=(
            average_validation_return
        ),

        average_validation_sharpe=(
            average_validation_sharpe
        ),

        average_validation_drawdown=(
            average_validation_drawdown
        ),

        average_return_retention=(
            average_return_retention
        ),

        parameter_stability_score=(
            parameter_stability_score
        ),
    )

    entry_values = [
        window.entry_score
        for window in successful_windows
    ]

    exit_values = [
        window.exit_score
        for window in successful_windows
    ]

    stop_values = [
        window.stop_atr_multiple
        for window in successful_windows
    ]

    target_values = [
        window.target_atr_multiple
        for window in successful_windows
    ]

    holding_values = [
        window.maximum_holding_days
        for window in successful_windows
    ]

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return WalkForwardValidationResult(
        version="V7.4",

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

        training_window_rows=(
            training_window_rows
        ),

        validation_window_rows=(
            validation_window_rows
        ),

        step_rows=step_rows,

        estimated_trading_days_per_year=(
            estimated_trading_days_per_year
        ),

        total_windows=len(
            windows
        ),

        successful_windows=len(
            successful_windows
        ),

        failed_windows=len(
            failed_windows
        ),

        profitable_windows=len(
            profitable_windows
        ),

        acceptable_windows=len(
            acceptable_windows
        ),

        beat_default_return_windows=len(
            beat_default_return_windows
        ),

        beat_default_sharpe_windows=len(
            beat_default_sharpe_windows
        ),

        profitable_window_percent=(
            profitable_percent
        ),

        acceptable_window_percent=(
            acceptable_percent
        ),

        beat_default_return_percent=(
            beat_default_return_percent
        ),

        beat_default_sharpe_percent=(
            beat_default_sharpe_percent
        ),

        average_validation_return_percent=(
            average_validation_return
        ),

        median_validation_return_percent=(
            safe_median(
                validation_returns
            )
        ),

        average_default_return_percent=(
            safe_average(
                default_returns
            )
        ),

        average_excess_return_percent=(
            safe_average(
                excess_returns
            )
        ),

        median_excess_return_percent=(
            safe_median(
                excess_returns
            )
        ),

        average_validation_sharpe_ratio=(
            average_validation_sharpe
        ),

        average_default_sharpe_ratio=(
            safe_average(
                default_sharpes
            )
        ),

        average_validation_drawdown_percent=(
            average_validation_drawdown
        ),

        worst_validation_drawdown_percent=(
            round(
                min(
                    validation_drawdowns
                ),
                2,
            )
            if validation_drawdowns
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

        total_validation_trades=sum(
            window.validation_total_trades
            for window in successful_windows
        ),

        average_return_retention_percent=(
            average_return_retention
        ),

        average_sharpe_retention_percent=(
            safe_average(
                sharpe_retentions
            )
        ),

        parameter_stability_score=(
            parameter_stability_score
        ),

        most_common_entry_score=(
            safe_float(
                get_most_common_value(
                    entry_values
                )
            )
            if entry_values
            else None
        ),

        most_common_exit_score=(
            safe_float(
                get_most_common_value(
                    exit_values
                )
            )
            if exit_values
            else None
        ),

        most_common_stop_atr=(
            safe_float(
                get_most_common_value(
                    stop_values
                )
            )
            if stop_values
            else None
        ),

        most_common_target_atr=(
            safe_float(
                get_most_common_value(
                    target_values
                )
            )
            if target_values
            else None
        ),

        most_common_holding_days=(
            int(
                get_most_common_value(
                    holding_values
                )
            )
            if holding_values
            else None
        ),

        validation_status=(
            validation_status
        ),

        overfitting_warning=(
            overfitting_warning
        ),

        reasons=reasons,
        warnings=warnings,

        windows=[
            window.to_dict()
            for window in windows
        ],
    )


def save_walk_forward_result(
    result: WalkForwardValidationResult,
) -> tuple[Path, Path]:
    """
    Walk-Forward 결과를 JSON으로 저장합니다.
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
            f"{result.symbol}_walk_forward_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_walk_forward_"
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


def print_walk_forward_result(
    result: WalkForwardValidationResult,
) -> None:
    """
    전체 Walk-Forward 결과를 출력합니다.
    """

    print()
    print("=" * 132)
    print(
        f"{result.symbol} V7.4 "
        "WALK-FORWARD VALIDATION RESULT"
    )
    print("=" * 132)

    print(
        f"Full period              : "
        f"{result.full_start_date} "
        f"to {result.full_end_date}"
    )

    print(
        f"Total windows            : "
        f"{result.total_windows}"
    )

    print(
        f"Successful windows       : "
        f"{result.successful_windows}"
    )

    print(
        f"Failed windows           : "
        f"{result.failed_windows}"
    )

    print(
        f"Validation status        : "
        f"{result.validation_status}"
    )

    print(
        f"Overfitting warning      : "
        f"{result.overfitting_warning}"
    )

    print()
    print("CONSISTENCY")
    print("-" * 132)

    print(
        f"Profitable windows       : "
        f"{result.profitable_windows}/"
        f"{result.successful_windows} "
        f"({result.profitable_window_percent:.2f}%)"
    )

    print(
        f"Acceptable windows       : "
        f"{result.acceptable_windows}/"
        f"{result.successful_windows} "
        f"({result.acceptable_window_percent:.2f}%)"
    )

    print(
        f"Beat default return      : "
        f"{result.beat_default_return_windows}/"
        f"{result.successful_windows} "
        f"({result.beat_default_return_percent:.2f}%)"
    )

    print(
        f"Beat default Sharpe      : "
        f"{result.beat_default_sharpe_windows}/"
        f"{result.successful_windows} "
        f"({result.beat_default_sharpe_percent:.2f}%)"
    )

    print()
    print("AVERAGE VALIDATION PERFORMANCE")
    print("-" * 132)

    print(
        f"Average strategy return  : "
        f"{result.average_validation_return_percent:.2f}%"
    )

    print(
        f"Median strategy return   : "
        f"{result.median_validation_return_percent:.2f}%"
    )

    print(
        f"Average default return   : "
        f"{result.average_default_return_percent:.2f}%"
    )

    print(
        f"Average excess return    : "
        f"{result.average_excess_return_percent:.2f}%"
    )

    print(
        f"Median excess return     : "
        f"{result.median_excess_return_percent:.2f}%"
    )

    print(
        f"Average strategy Sharpe  : "
        f"{result.average_validation_sharpe_ratio:.2f}"
    )

    print(
        f"Average default Sharpe   : "
        f"{result.average_default_sharpe_ratio:.2f}"
    )

    print(
        f"Average drawdown         : "
        f"{result.average_validation_drawdown_percent:.2f}%"
    )

    print(
        f"Worst drawdown           : "
        f"{result.worst_validation_drawdown_percent:.2f}%"
    )

    print(
        f"Average profit factor    : "
        f"{result.average_profit_factor:.2f}"
    )

    print(
        f"Average win rate         : "
        f"{result.average_win_rate_percent:.2f}%"
    )

    print(
        f"Total validation trades  : "
        f"{result.total_validation_trades}"
    )

    print()
    print("PERFORMANCE RETENTION")
    print("-" * 132)

    print(
        f"Average return retention : "
        f"{result.average_return_retention_percent:.2f}%"
    )

    print(
        f"Average Sharpe retention : "
        f"{result.average_sharpe_retention_percent:.2f}%"
    )

    print()
    print("PARAMETER STABILITY")
    print("-" * 132)

    print(
        f"Parameter stability      : "
        f"{result.parameter_stability_score:.2f}/100"
    )

    print(
        f"Most common entry        : "
        f"{result.most_common_entry_score}"
    )

    print(
        f"Most common exit         : "
        f"{result.most_common_exit_score}"
    )

    print(
        f"Most common stop ATR     : "
        f"{result.most_common_stop_atr}"
    )

    print(
        f"Most common target ATR   : "
        f"{result.most_common_target_atr}"
    )

    print(
        f"Most common hold days    : "
        f"{result.most_common_holding_days}"
    )

    print()
    print("WINDOW RESULTS")
    print("-" * 132)

    print(
        f"{'No.':<5}"
        f"{'Validation Period':<25}"
        f"{'Entry':>8}"
        f"{'Exit':>7}"
        f"{'Stop':>8}"
        f"{'Target':>9}"
        f"{'Hold':>7}"
        f"{'Return':>11}"
        f"{'Default':>11}"
        f"{'Sharpe':>9}"
        f"{'DD':>10}"
        f"{'Trades':>9}"
        f"{'Status':>12}"
    )

    print("-" * 132)

    for window in result.windows:
        validation_period = (
            f"{window['validation_start_date']} "
            f"to {window['validation_end_date']}"
        )

        if not window[
            "validation_success"
        ]:
            print(
                f"{window['window_number']:<5}"
                f"{validation_period:<25}"
                f"{'FAILED':>107}"
            )
            continue

        status = (
            "ACCEPTABLE"
            if window[
                "acceptable"
            ]
            else "WEAK"
        )

        print(
            f"{window['window_number']:<5}"
            f"{validation_period:<25}"
            f"{window['entry_score']:>8.0f}"
            f"{window['exit_score']:>7.0f}"
            f"{window['stop_atr_multiple']:>8.2f}"
            f"{window['target_atr_multiple']:>9.2f}"
            f"{window['maximum_holding_days']:>7}"
            f"{window['validation_return_percent']:>10.2f}%"
            f"{window['default_return_percent']:>10.2f}%"
            f"{window['validation_sharpe_ratio']:>9.2f}"
            f"{window['validation_drawdown_percent']:>9.2f}%"
            f"{window['validation_total_trades']:>9}"
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
        "주의: Walk-Forward 검증은 단일 검증보다 "
        "신뢰도가 높지만 미래 수익을 보장하지 않습니다."
    )