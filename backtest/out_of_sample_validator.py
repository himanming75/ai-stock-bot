import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from backtest.recommendation_backtester import (
    StrategyBacktestResult,
    run_recommendation_backtest,
)
from backtest.strategy_optimizer import (
    StrategyOptimizationResult,
    run_strategy_optimization,
)
from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "out_of_sample"
)


@dataclass
class OutOfSampleValidationResult:
    """
    V7.3 Out-of-Sample 검증 결과입니다.

    전체 데이터를 훈련 구간과 검증 구간으로 나누고,
    훈련 구간에서 선택한 파라미터를
    검증 구간에 한 번만 적용합니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    total_rows: int
    training_rows: int
    validation_rows: int

    training_ratio_percent: float
    validation_ratio_percent: float

    full_start_date: str
    full_end_date: str

    training_start_date: str
    training_end_date: str

    validation_start_date: str
    validation_end_date: str

    best_parameters: dict[str, Any] | None

    training_optimization_score: float
    training_return_percent: float
    training_sharpe_ratio: float
    training_drawdown_percent: float
    training_profit_factor: float
    training_total_trades: int

    validation_success: bool
    validation_return_percent: float
    validation_buy_hold_return_percent: float
    validation_excess_return_percent: float
    validation_sharpe_ratio: float
    validation_drawdown_percent: float
    validation_profit_factor: float
    validation_win_rate_percent: float
    validation_total_trades: int

    default_validation_return_percent: float
    default_validation_sharpe_ratio: float
    default_validation_drawdown_percent: float

    return_retention_percent: float
    sharpe_retention_percent: float

    validation_status: str
    overfitting_warning: bool
    reasons: list[str]
    warnings: list[str]

    optimizer_result: dict[str, Any]
    validation_result: dict[str, Any]
    default_validation_result: dict[str, Any]

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


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    값을 안전하게 float로 변환합니다.
    """

    try:
        converted = float(value)

        if pd.isna(converted):
            return default

        return converted

    except (
        TypeError,
        ValueError,
    ):
        return default


def format_date(
    value: Any,
) -> str:
    """
    날짜를 YYYY-MM-DD 문자열로 변환합니다.
    """

    return pd.Timestamp(
        value
    ).strftime(
        "%Y-%m-%d"
    )


def clean_market_data(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    다운로드한 시장 데이터를 검증하고 정리합니다.
    """

    if data is None or data.empty:
        raise ValueError(
            "시장 데이터가 비어 있습니다."
        )

    required_columns = {
        "Open",
        "High",
        "Low",
        "Close",
    }

    missing_columns = (
        required_columns
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "필요한 시장 데이터 열이 없습니다: "
            f"{sorted(missing_columns)}"
        )

    cleaned = (
        data.copy()
        .sort_index()
    )

    cleaned = cleaned[
        ~cleaned.index.duplicated(
            keep="last"
        )
    ]

    cleaned = cleaned.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close",
        ]
    )

    if len(cleaned) < 300:
        raise ValueError(
            "Out-of-Sample 검증을 수행하기에는 "
            "시장 데이터가 너무 적습니다. "
            f"현재 행 수: {len(cleaned)}"
        )

    return cleaned


def split_train_validation_data(
    data: pd.DataFrame,
    training_ratio: float = 0.70,
    minimum_training_rows: int = 200,
    minimum_validation_rows: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    시간 순서를 유지하면서 데이터를 분리합니다.

    무작위 섞기를 하지 않습니다.

    앞부분:
        전략 파라미터 최적화용

    뒷부분:
        Out-of-Sample 검증용
    """

    if not 0.50 <= training_ratio <= 0.90:
        raise ValueError(
            "training_ratio는 "
            "0.50 이상 0.90 이하여야 합니다."
        )

    split_index = int(
        len(data)
        * training_ratio
    )

    training_data = (
        data.iloc[
            :split_index
        ]
        .copy()
    )

    validation_data = (
        data.iloc[
            split_index:
        ]
        .copy()
    )

    if (
        len(training_data)
        < minimum_training_rows
    ):
        raise ValueError(
            "훈련 데이터가 너무 적습니다. "
            f"현재 {len(training_data)}행, "
            f"최소 {minimum_training_rows}행이 필요합니다."
        )

    if (
        len(validation_data)
        < minimum_validation_rows
    ):
        raise ValueError(
            "검증 데이터가 너무 적습니다. "
            f"현재 {len(validation_data)}행, "
            f"최소 {minimum_validation_rows}행이 필요합니다."
        )

    return (
        training_data,
        validation_data,
    )


def run_backtest_with_dataframe(
    symbol: str,
    data: pd.DataFrame,
    initial_cash: float,
    position_percent: float,
    entry_score: float,
    exit_score: float,
    stop_atr_multiple: float,
    target_atr_multiple: float,
    maximum_holding_days: int,
    commission_per_trade: float,
    dataset_name: str,
) -> StrategyBacktestResult:
    """
    기존 V7.0 백테스트 엔진에
    지정된 DataFrame만 전달하여 실행합니다.

    기존 recommendation_backtester.py의
    소스코드는 수정하지 않습니다.
    """

    supplied_data = data.copy()

    def mocked_get_history(
        symbol: str,
        period: str,
        interval: str,
    ) -> pd.DataFrame:
        del symbol
        del period
        del interval

        return supplied_data.copy()

    with patch(
        "backtest.recommendation_backtester.get_history",
        side_effect=mocked_get_history,
    ):
        result = run_recommendation_backtest(
            symbol=symbol,

            period=dataset_name,
            interval="1d",

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

    return result


def run_optimizer_with_dataframe(
    symbol: str,
    training_data: pd.DataFrame,
    initial_cash: float,
    commission_per_trade: float,
    entry_scores: list[float],
    exit_scores: list[float],
    stop_atr_multiples: list[float],
    target_atr_multiples: list[float],
    maximum_holding_days_list: list[int],
    position_percents: list[float],
    minimum_trades: int,
    top_n: int,
) -> StrategyOptimizationResult:
    """
    V7.2 Optimizer가 전체 데이터를 다시 받지 않고
    훈련 구간만 사용하도록 실행합니다.
    """

    supplied_data = training_data.copy()

    def mocked_get_history(
        symbol: str,
        period: str,
        interval: str,
    ) -> pd.DataFrame:
        del symbol
        del period
        del interval

        return supplied_data.copy()

    with patch(
        "backtest.recommendation_backtester.get_history",
        side_effect=mocked_get_history,
    ):
        optimization_result = (
            run_strategy_optimization(
                symbol=symbol,

                period="TRAINING_DATA",
                interval="1d",

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
                    minimum_trades
                ),

                top_n=top_n,
            )
        )

    return optimization_result


def calculate_retention_percent(
    training_value: float,
    validation_value: float,
) -> float:
    """
    훈련 성과가 검증 구간에서
    얼마나 유지됐는지 계산합니다.
    """

    training_value = safe_float(
        training_value
    )

    validation_value = safe_float(
        validation_value
    )

    if training_value <= 0:
        return 0.0

    retention = (
        validation_value
        / training_value
    ) * 100.0

    return round(
        retention,
        2,
    )


def evaluate_validation_quality(
    training_return: float,
    training_sharpe: float,
    validation_result: StrategyBacktestResult,
    default_result: StrategyBacktestResult,
    minimum_validation_trades: int,
) -> tuple[
    str,
    bool,
    list[str],
    list[str],
]:
    """
    Out-of-Sample 성과를 평가합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if not validation_result.success:
        return (
            "FAILED",
            True,
            [
                "검증 백테스트 실행에 실패했습니다."
            ],
            [
                validation_result.error_message
                or "알 수 없는 검증 오류"
            ],
        )

    validation_return = (
        validation_result
        .total_return_percent
    )

    validation_sharpe = (
        validation_result
        .sharpe_ratio
    )

    validation_drawdown = abs(
        validation_result
        .maximum_drawdown_percent
    )

    validation_profit_factor = (
        validation_result
        .profit_factor
    )

    validation_trades = (
        validation_result
        .total_trades
    )

    return_retention = (
        calculate_retention_percent(
            training_value=training_return,
            validation_value=validation_return,
        )
    )

    sharpe_retention = (
        calculate_retention_percent(
            training_value=training_sharpe,
            validation_value=validation_sharpe,
        )
    )

    score = 0

    if validation_return > 0:
        score += 2

        reasons.append(
            "검증 구간 전략 수익률이 "
            "플러스입니다."
        )

    else:
        warnings.append(
            "검증 구간 전략 수익률이 "
            "0% 이하입니다."
        )

    if validation_sharpe >= 1.0:
        score += 2

        reasons.append(
            "검증 Sharpe Ratio가 "
            "1.0 이상입니다."
        )

    elif validation_sharpe >= 0.5:
        score += 1

        reasons.append(
            "검증 Sharpe Ratio가 "
            "0.5 이상입니다."
        )

    else:
        warnings.append(
            "검증 Sharpe Ratio가 "
            "0.5 미만입니다."
        )

    if validation_drawdown <= 10.0:
        score += 2

        reasons.append(
            "검증 최대 낙폭이 "
            "10% 이내입니다."
        )

    elif validation_drawdown <= 20.0:
        score += 1

    else:
        warnings.append(
            "검증 최대 낙폭이 "
            "20%를 초과합니다."
        )

    if validation_profit_factor >= 1.2:
        score += 1

        reasons.append(
            "검증 Profit Factor가 "
            "1.2 이상입니다."
        )

    else:
        warnings.append(
            "검증 Profit Factor가 "
            "1.2 미만입니다."
        )

    if (
        validation_trades
        >= minimum_validation_trades
    ):
        score += 1

        reasons.append(
            "검증 거래 횟수가 "
            "최소 기준을 충족합니다."
        )

    else:
        warnings.append(
            "검증 거래 표본 수가 적습니다. "
            f"현재 {validation_trades}회, "
            f"기준 {minimum_validation_trades}회입니다."
        )

    if return_retention >= 50.0:
        score += 1

        reasons.append(
            "훈련 수익률 대비 검증 수익률의 "
            "유지율이 50% 이상입니다."
        )

    elif return_retention < 20.0:
        warnings.append(
            "검증 수익률 유지율이 매우 낮아 "
            "과최적화 가능성이 있습니다."
        )

    if sharpe_retention >= 50.0:
        score += 1

        reasons.append(
            "훈련 Sharpe 대비 검증 Sharpe의 "
            "유지율이 50% 이상입니다."
        )

    elif sharpe_retention < 20.0:
        warnings.append(
            "검증 Sharpe 유지율이 매우 낮습니다."
        )

    if (
        default_result.success
        and validation_return
        >= default_result.total_return_percent
    ):
        score += 1

        reasons.append(
            "최적 파라미터가 검증 구간에서 "
            "기본 파라미터 이상의 수익률을 기록했습니다."
        )

    overfitting_warning = (
        validation_return <= 0
        or validation_sharpe < 0.5
        or return_retention < 20.0
        or validation_trades
        < minimum_validation_trades
    )

    if score >= 9:
        status = "ROBUST"

    elif score >= 6:
        status = "ACCEPTABLE"

    elif score >= 4:
        status = "WEAK"

    else:
        status = "OVERFIT_RISK"

    return (
        status,
        overfitting_warning,
        reasons,
        warnings,
    )


def run_out_of_sample_validation(
    symbol: str,
    period: str = "10y",
    interval: str = "1d",
    training_ratio: float = 0.70,
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
    top_n: int = 10,
) -> OutOfSampleValidationResult:
    """
    V7.3 Out-of-Sample 검증을 실행합니다.
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

    started_at = datetime.now()

    print()
    print("=" * 92)
    print(
        f"{normalized_symbol} V7.3 "
        "OUT-OF-SAMPLE VALIDATION"
    )
    print("=" * 92)

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

    (
        training_data,
        validation_data,
    ) = split_train_validation_data(
        data=full_data,
        training_ratio=training_ratio,
    )

    print(
        f"Full rows            : "
        f"{len(full_data)}"
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

    print("=" * 92)

    print()
    print(
        "Optimizing parameters on "
        "training data only..."
    )

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

    if optimizer_result.best_trial is None:
        raise RuntimeError(
            "훈련 구간에서 사용할 수 있는 "
            "최적 파라미터를 찾지 못했습니다."
        )

    best = optimizer_result.best_trial

    print()
    print("=" * 92)
    print("BEST TRAINING PARAMETERS")
    print("=" * 92)

    print(
        f"Entry score          : "
        f"{best['entry_score']:.2f}"
    )

    print(
        f"Exit score           : "
        f"{best['exit_score']:.2f}"
    )

    print(
        f"Stop ATR             : "
        f"{best['stop_atr_multiple']:.2f}"
    )

    print(
        f"Target ATR           : "
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

    print(
        f"Training return      : "
        f"{best['strategy_return_percent']:.2f}%"
    )

    print(
        f"Training Sharpe      : "
        f"{best['sharpe_ratio']:.2f}"
    )

    print("=" * 92)

    print()
    print(
        "Running one-time validation "
        "on unseen data..."
    )

    validation_result = (
        run_backtest_with_dataframe(
            symbol=normalized_symbol,

            data=validation_data,

            initial_cash=initial_cash,

            position_percent=(
                best["position_percent"]
            ),

            entry_score=(
                best["entry_score"]
            ),

            exit_score=(
                best["exit_score"]
            ),

            stop_atr_multiple=(
                best["stop_atr_multiple"]
            ),

            target_atr_multiple=(
                best["target_atr_multiple"]
            ),

            maximum_holding_days=(
                best["maximum_holding_days"]
            ),

            commission_per_trade=(
                commission_per_trade
            ),

            dataset_name=(
                "OUT_OF_SAMPLE_VALIDATION"
            ),
        )
    )

    print()
    print(
        "Running default parameter "
        "validation benchmark..."
    )

    default_validation_result = (
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
                "DEFAULT_VALIDATION_BENCHMARK"
            ),
        )
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

    return_retention = (
        calculate_retention_percent(
            training_value=training_return,
            validation_value=validation_return,
        )
    )

    sharpe_retention = (
        calculate_retention_percent(
            training_value=training_sharpe,
            validation_value=validation_sharpe,
        )
    )

    (
        validation_status,
        overfitting_warning,
        reasons,
        warnings,
    ) = evaluate_validation_quality(
        training_return=training_return,
        training_sharpe=training_sharpe,

        validation_result=(
            validation_result
        ),

        default_result=(
            default_validation_result
        ),

        minimum_validation_trades=(
            minimum_validation_trades
        ),
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return OutOfSampleValidationResult(
        version="V7.3",

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

        total_rows=len(
            full_data
        ),

        training_rows=len(
            training_data
        ),

        validation_rows=len(
            validation_data
        ),

        training_ratio_percent=round(
            training_ratio * 100.0,
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

        full_start_date=format_date(
            full_data.index[0]
        ),

        full_end_date=format_date(
            full_data.index[-1]
        ),

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

        best_parameters={
            "entry_score": (
                best["entry_score"]
            ),

            "exit_score": (
                best["exit_score"]
            ),

            "stop_atr_multiple": (
                best["stop_atr_multiple"]
            ),

            "target_atr_multiple": (
                best["target_atr_multiple"]
            ),

            "maximum_holding_days": (
                best[
                    "maximum_holding_days"
                ]
            ),

            "position_percent": (
                best["position_percent"]
            ),
        },

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

        validation_success=(
            validation_result.success
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

        validation_drawdown_percent=safe_float(
            validation_result
            .maximum_drawdown_percent
        ),

        validation_profit_factor=safe_float(
            validation_result
            .profit_factor
        ),

        validation_win_rate_percent=safe_float(
            validation_result
            .win_rate_percent
        ),

        validation_total_trades=int(
            validation_result
            .total_trades
        ),

        default_validation_return_percent=safe_float(
            default_validation_result
            .total_return_percent
        ),

        default_validation_sharpe_ratio=safe_float(
            default_validation_result
            .sharpe_ratio
        ),

        default_validation_drawdown_percent=safe_float(
            default_validation_result
            .maximum_drawdown_percent
        ),

        return_retention_percent=(
            return_retention
        ),

        sharpe_retention_percent=(
            sharpe_retention
        ),

        validation_status=(
            validation_status
        ),

        overfitting_warning=(
            overfitting_warning
        ),

        reasons=reasons,
        warnings=warnings,

        optimizer_result=(
            optimizer_result.to_dict()
        ),

        validation_result=(
            validation_result.to_dict()
        ),

        default_validation_result=(
            default_validation_result
            .to_dict()
        ),
    )


def save_out_of_sample_result(
    result: OutOfSampleValidationResult,
) -> tuple[Path, Path]:
    """
    V7.3 검증 결과를 JSON 파일로 저장합니다.
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
            f"{result.symbol}_out_of_sample_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_out_of_sample_"
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


def print_out_of_sample_result(
    result: OutOfSampleValidationResult,
) -> None:
    """
    V7.3 검증 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 100)
    print(
        f"{result.symbol} V7.3 "
        "OUT-OF-SAMPLE VALIDATION RESULT"
    )
    print("=" * 100)

    print(
        f"Full period          : "
        f"{result.full_start_date} "
        f"to {result.full_end_date}"
    )

    print(
        f"Training period      : "
        f"{result.training_start_date} "
        f"to {result.training_end_date}"
    )

    print(
        f"Validation period    : "
        f"{result.validation_start_date} "
        f"to {result.validation_end_date}"
    )

    print(
        f"Training rows        : "
        f"{result.training_rows}"
    )

    print(
        f"Validation rows      : "
        f"{result.validation_rows}"
    )

    print()
    print("SELECTED PARAMETERS")
    print("-" * 100)

    parameters = (
        result.best_parameters
        or {}
    )

    print(
        f"Entry score          : "
        f"{parameters.get('entry_score', 'N/A')}"
    )

    print(
        f"Exit score           : "
        f"{parameters.get('exit_score', 'N/A')}"
    )

    print(
        f"Stop ATR             : "
        f"{parameters.get('stop_atr_multiple', 'N/A')}"
    )

    print(
        f"Target ATR           : "
        f"{parameters.get('target_atr_multiple', 'N/A')}"
    )

    print(
        f"Maximum holding days : "
        f"{parameters.get('maximum_holding_days', 'N/A')}"
    )

    print()
    print("TRAINING PERFORMANCE")
    print("-" * 100)

    print(
        f"Optimization score   : "
        f"{result.training_optimization_score:.2f}/100"
    )

    print(
        f"Return               : "
        f"{result.training_return_percent:.2f}%"
    )

    print(
        f"Sharpe ratio         : "
        f"{result.training_sharpe_ratio:.2f}"
    )

    print(
        f"Maximum drawdown     : "
        f"{result.training_drawdown_percent:.2f}%"
    )

    print(
        f"Profit factor        : "
        f"{result.training_profit_factor:.2f}"
    )

    print(
        f"Total trades         : "
        f"{result.training_total_trades}"
    )

    print()
    print("UNSEEN VALIDATION PERFORMANCE")
    print("-" * 100)

    print(
        f"Validation status    : "
        f"{result.validation_status}"
    )

    print(
        f"Strategy return      : "
        f"{result.validation_return_percent:.2f}%"
    )

    print(
        f"Buy and hold return  : "
        f"{result.validation_buy_hold_return_percent:.2f}%"
    )

    print(
        f"Excess return        : "
        f"{result.validation_excess_return_percent:.2f}%"
    )

    print(
        f"Sharpe ratio         : "
        f"{result.validation_sharpe_ratio:.2f}"
    )

    print(
        f"Maximum drawdown     : "
        f"{result.validation_drawdown_percent:.2f}%"
    )

    print(
        f"Profit factor        : "
        f"{result.validation_profit_factor:.2f}"
    )

    print(
        f"Win rate             : "
        f"{result.validation_win_rate_percent:.2f}%"
    )

    print(
        f"Total trades         : "
        f"{result.validation_total_trades}"
    )

    print()
    print("DEFAULT PARAMETER BENCHMARK")
    print("-" * 100)

    print(
        f"Default return       : "
        f"{result.default_validation_return_percent:.2f}%"
    )

    print(
        f"Default Sharpe       : "
        f"{result.default_validation_sharpe_ratio:.2f}"
    )

    print(
        f"Default drawdown     : "
        f"{result.default_validation_drawdown_percent:.2f}%"
    )

    print()
    print("PERFORMANCE RETENTION")
    print("-" * 100)

    print(
        f"Return retention     : "
        f"{result.return_retention_percent:.2f}%"
    )

    print(
        f"Sharpe retention     : "
        f"{result.sharpe_retention_percent:.2f}%"
    )

    print(
        f"Overfitting warning  : "
        f"{result.overfitting_warning}"
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

    print("=" * 100)

    print(
        "주의: Out-of-Sample 검증도 미래 수익을 "
        "보장하지 않으며, 반복적으로 검증 구간을 "
        "확인하면 다시 과최적화될 수 있습니다."
    )