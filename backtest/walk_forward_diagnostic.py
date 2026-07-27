import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

WALK_FORWARD_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "walk_forward"
)

DIAGNOSTIC_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "walk_forward_diagnostic"
)


@dataclass
class WalkForwardWindowDiagnostic:
    """
    Walk-Forward의 한 검증 구간 분석 결과입니다.
    """

    window_number: int

    training_start: str
    training_end: str

    validation_start: str
    validation_end: str

    entry_score: float
    exit_score: float

    stop_atr_multiple: float
    target_atr_multiple: float
    maximum_holding_days: int
    position_percent: float

    strategy_return_percent: float
    default_return_percent: float
    excess_return_percent: float

    sharpe_ratio: float
    default_sharpe_ratio: float

    maximum_drawdown_percent: float
    profit_factor: float
    win_rate_percent: float
    total_trades: int

    return_retention_percent: float
    sharpe_retention_percent: float

    return_score: float
    sharpe_score: float
    drawdown_score: float
    profit_factor_score: float
    consistency_score: float

    diagnostic_score: float
    diagnostic_status: str

    profitable: bool
    beat_default_return: bool
    beat_default_sharpe: bool
    acceptable: bool

    problems: list[str]
    strengths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WalkForwardDiagnosticResult:
    """
    V8.1 Walk-Forward 전체 진단 결과입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    source_file: str

    total_windows: int
    successful_windows: int
    failed_windows: int

    profitable_windows: int
    profitable_percent: float

    acceptable_windows: int
    acceptable_percent: float

    beat_default_return_windows: int
    beat_default_return_percent: float

    beat_default_sharpe_windows: int
    beat_default_sharpe_percent: float

    average_strategy_return_percent: float
    median_strategy_return_percent: float
    worst_strategy_return_percent: float
    best_strategy_return_percent: float

    average_default_return_percent: float
    average_excess_return_percent: float

    average_sharpe_ratio: float
    median_sharpe_ratio: float
    worst_sharpe_ratio: float
    best_sharpe_ratio: float

    average_drawdown_percent: float
    worst_drawdown_percent: float

    average_profit_factor: float
    average_win_rate_percent: float
    total_validation_trades: int

    average_return_retention_percent: float
    average_sharpe_retention_percent: float

    parameter_stability_score: float
    performance_consistency_score: float
    recent_performance_score: float
    overall_diagnostic_score: float

    validation_status: str
    recent_trend: str
    overfitting_warning: bool

    best_window_number: int | None
    worst_window_number: int | None

    most_common_entry_score: float | None
    most_common_exit_score: float | None
    most_common_stop_atr: float | None
    most_common_target_atr: float | None
    most_common_holding_days: int | None

    critical_problems: list[str]
    strengths: list[str]
    recommendations: list[str]

    windows: list[dict[str, Any]]

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
        if value is None:
            return default

        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    값을 안전하게 int로 변환합니다.
    """

    try:
        if value is None:
            return default

        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_bool(
    value: Any,
    default: bool = False,
) -> bool:
    """
    여러 형태의 값을 bool 값으로 변환합니다.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {
            "true",
            "yes",
            "1",
        }:
            return True

        if normalized in {
            "false",
            "no",
            "0",
        }:
            return False

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return bool(value)

    return default


def clamp_score(
    score: float,
) -> float:
    """
    점수를 0~100 사이로 제한합니다.
    """

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


def first_value(
    data: dict[str, Any],
    keys: list[str],
    default: Any = None,
) -> Any:
    """
    여러 후보 키 중 첫 번째 존재하는 값을 반환합니다.
    """

    for key in keys:
        if (
            key in data
            and data[key] is not None
        ):
            return data[key]

    return default


def nested_first_value(
    data: dict[str, Any],
    paths: list[list[str]],
    default: Any = None,
) -> Any:
    """
    여러 중첩 키 경로 중 첫 번째 값을 반환합니다.
    """

    for path in paths:
        current: Any = data
        found = True

        for key in path:
            if (
                isinstance(current, dict)
                and key in current
            ):
                current = current[key]

            else:
                found = False
                break

        if (
            found
            and current is not None
        ):
            return current

    return default


def safe_average(
    values: list[float],
) -> float:
    """
    평균을 안전하게 계산합니다.
    """

    if not values:
        return 0.0

    return round(
        float(mean(values)),
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

    return round(
        float(median(values)),
        2,
    )


def safe_percent(
    numerator: int,
    denominator: int,
) -> float:
    """
    비율을 퍼센트로 계산합니다.
    """

    if denominator <= 0:
        return 0.0

    return round(
        numerator
        / denominator
        * 100.0,
        2,
    )


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 정규화합니다.
    """

    normalized = (
        symbol
        .strip()
        .upper()
    )

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def normalize_status(
    value: Any,
) -> str:
    """
    상태 문자열을 대문자로 정규화합니다.
    """

    return str(
        value
        or "UNKNOWN"
    ).strip().upper()


def mode_value(
    values: list[Any],
) -> Any:
    """
    목록에서 가장 많이 나타나는 값을 반환합니다.
    """

    if not values:
        return None

    counts: dict[Any, int] = {}

    for value in values:
        counts[value] = (
            counts.get(
                value,
                0,
            )
            + 1
        )

    return max(
        counts,
        key=counts.get,
    )


def find_walk_forward_latest_file(
    symbol: str,
) -> Path:
    """
    V7.4 Walk-Forward latest JSON 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    preferred_paths = [
        (
            WALK_FORWARD_DIRECTORY
            / (
                f"{normalized_symbol}_"
                "walk_forward_latest.json"
            )
        ),
        (
            WALK_FORWARD_DIRECTORY
            / (
                f"{normalized_symbol}_"
                "walk_forward_validation_latest.json"
            )
        ),
    ]

    for path in preferred_paths:
        if path.exists():
            return path

    if not WALK_FORWARD_DIRECTORY.exists():
        raise FileNotFoundError(
            f"Walk-Forward 폴더가 없습니다: "
            f"{WALK_FORWARD_DIRECTORY}"
        )

    candidates = [
        path
        for path in WALK_FORWARD_DIRECTORY.glob(
            f"{normalized_symbol}_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not candidates:
        raise FileNotFoundError(
            f"{normalized_symbol} Walk-Forward "
            "결과 JSON 파일을 찾을 수 없습니다."
        )

    return max(
        candidates,
        key=lambda path: path.stat().st_mtime,
    )


def load_walk_forward_result(
    path: Path,
) -> dict[str, Any]:
    """
    Walk-Forward 결과 JSON을 읽습니다.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"파일이 없습니다: {path}"
        )

    with path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(
            file
        )

    if not isinstance(payload, dict):
        raise ValueError(
            "Walk-Forward JSON 최상위 데이터가 "
            "객체가 아닙니다."
        )

    return payload


def extract_window_list(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    다양한 JSON 구조에서 Walk-Forward 구간 목록을 찾습니다.
    """

    candidate_keys = [
        "windows",
        "window_results",
        "validation_windows",
        "results",
        "walk_forward_windows",
    ]

    for key in candidate_keys:
        value = data.get(key)

        if isinstance(value, list):
            dictionaries = [
                item
                for item in value
                if isinstance(item, dict)
            ]

            if dictionaries:
                return dictionaries

    nested_containers = [
        "report",
        "result",
        "summary",
        "walk_forward",
        "validation",
    ]

    for container_key in nested_containers:
        container = data.get(
            container_key
        )

        if not isinstance(
            container,
            dict,
        ):
            continue

        for key in candidate_keys:
            value = container.get(
                key
            )

            if isinstance(value, list):
                dictionaries = [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

                if dictionaries:
                    return dictionaries

    raise ValueError(
        "Walk-Forward JSON에서 검증 구간 목록을 "
        "찾을 수 없습니다."
    )


def extract_parameter(
    window: dict[str, Any],
    keys: list[str],
    default: Any = 0,
) -> Any:
    """
    Window 또는 parameters 내부에서 파라미터를 찾습니다.
    """

    direct = first_value(
        window,
        keys,
        None,
    )

    if direct is not None:
        return direct

    parameter_containers = [
        "parameters",
        "selected_parameters",
        "best_parameters",
        "strategy_parameters",
    ]

    for container_name in parameter_containers:
        container = window.get(
            container_name
        )

        if isinstance(
            container,
            dict,
        ):
            nested = first_value(
                container,
                keys,
                None,
            )

            if nested is not None:
                return nested

    return default


def extract_metric(
    window: dict[str, Any],
    keys: list[str],
    default: Any = 0,
) -> Any:
    """
    Window 또는 결과 컨테이너 내부에서 지표를 찾습니다.
    """

    direct = first_value(
        window,
        keys,
        None,
    )

    if direct is not None:
        return direct

    result_containers = [
        "validation_result",
        "validation",
        "performance",
        "strategy_result",
        "result",
        "metrics",
    ]

    for container_name in result_containers:
        container = window.get(
            container_name
        )

        if isinstance(
            container,
            dict,
        ):
            nested = first_value(
                container,
                keys,
                None,
            )

            if nested is not None:
                return nested

    return default


def calculate_return_score(
    strategy_return: float,
    default_return: float,
) -> float:
    """
    검증 수익률 점수를 계산합니다.
    """

    score = 0.0

    if strategy_return > 0:
        score += 50.0

    if strategy_return >= 5.0:
        score += 15.0

    elif strategy_return >= 2.0:
        score += 10.0

    elif strategy_return > 0:
        score += 5.0

    if strategy_return > default_return:
        score += 25.0

    elif strategy_return >= (
        default_return * 0.75
    ):
        score += 12.0

    if default_return < 0 and strategy_return > 0:
        score += 10.0

    return clamp_score(
        score
    )


def calculate_sharpe_score(
    sharpe_ratio: float,
    default_sharpe: float,
) -> float:
    """
    Sharpe Ratio 점수를 계산합니다.
    """

    score = 0.0

    if sharpe_ratio >= 1.5:
        score += 70.0

    elif sharpe_ratio >= 1.0:
        score += 60.0

    elif sharpe_ratio >= 0.5:
        score += 45.0

    elif sharpe_ratio > 0:
        score += 25.0

    if sharpe_ratio > default_sharpe:
        score += 30.0

    elif sharpe_ratio >= (
        default_sharpe * 0.90
    ):
        score += 15.0

    return clamp_score(
        score
    )


def calculate_drawdown_score(
    drawdown_percent: float,
) -> float:
    """
    최대 낙폭 점수를 계산합니다.
    """

    absolute_drawdown = abs(
        drawdown_percent
    )

    if absolute_drawdown <= 5.0:
        return 100.0

    if absolute_drawdown <= 7.5:
        return 85.0

    if absolute_drawdown <= 10.0:
        return 70.0

    if absolute_drawdown <= 15.0:
        return 50.0

    if absolute_drawdown <= 20.0:
        return 30.0

    return 10.0


def calculate_profit_factor_score(
    profit_factor: float,
) -> float:
    """
    Profit Factor 점수를 계산합니다.
    """

    if profit_factor >= 2.0:
        return 100.0

    if profit_factor >= 1.5:
        return 85.0

    if profit_factor >= 1.3:
        return 70.0

    if profit_factor >= 1.1:
        return 55.0

    if profit_factor >= 1.0:
        return 40.0

    return 10.0


def determine_window_status(
    diagnostic_score: float,
    strategy_return: float,
    sharpe_ratio: float,
    profit_factor: float,
) -> str:
    """
    한 검증 구간의 상태를 결정합니다.
    """

    if (
        diagnostic_score >= 80.0
        and strategy_return > 0
        and sharpe_ratio >= 1.0
        and profit_factor >= 1.3
    ):
        return "ROBUST"

    if (
        diagnostic_score >= 60.0
        and strategy_return > 0
        and sharpe_ratio >= 0.5
        and profit_factor >= 1.1
    ):
        return "ACCEPTABLE"

    if strategy_return > 0:
        return "WEAK"

    return "FAILED"


def analyze_window(
    raw_window: dict[str, Any],
    window_number: int,
) -> WalkForwardWindowDiagnostic:
    """
    Walk-Forward의 한 구간을 분석합니다.
    """

    training_start = str(
        first_value(
            raw_window,
            [
                "training_start",
                "training_start_date",
                "train_start",
            ],
            "N/A",
        )
    )

    training_end = str(
        first_value(
            raw_window,
            [
                "training_end",
                "training_end_date",
                "train_end",
            ],
            "N/A",
        )
    )

    validation_start = str(
        first_value(
            raw_window,
            [
                "validation_start",
                "validation_start_date",
                "test_start",
            ],
            "N/A",
        )
    )

    validation_end = str(
        first_value(
            raw_window,
            [
                "validation_end",
                "validation_end_date",
                "test_end",
            ],
            "N/A",
        )
    )

    entry_score = safe_float(
        extract_parameter(
            raw_window,
            [
                "entry_score",
                "entry_threshold",
            ],
            0.0,
        )
    )

    exit_score = safe_float(
        extract_parameter(
            raw_window,
            [
                "exit_score",
                "exit_threshold",
            ],
            0.0,
        )
    )

    stop_atr_multiple = safe_float(
        extract_parameter(
            raw_window,
            [
                "stop_atr_multiple",
                "stop_atr",
                "stop_multiple",
            ],
            0.0,
        )
    )

    target_atr_multiple = safe_float(
        extract_parameter(
            raw_window,
            [
                "target_atr_multiple",
                "target_atr",
                "target_multiple",
            ],
            0.0,
        )
    )

    maximum_holding_days = safe_int(
        extract_parameter(
            raw_window,
            [
                "maximum_holding_days",
                "max_holding_days",
                "holding_days",
            ],
            0,
        )
    )

    position_percent = safe_float(
        extract_parameter(
            raw_window,
            [
                "position_percent",
                "position_size_percent",
            ],
            20.0,
        )
    )

    strategy_return = safe_float(
        extract_metric(
            raw_window,
            [
                "strategy_return",
                "strategy_return_percent",
                "validation_return",
                "validation_return_percent",
                "return_percent",
            ],
            0.0,
        )
    )

    default_return = safe_float(
        extract_metric(
            raw_window,
            [
                "default_return",
                "default_return_percent",
                "benchmark_return",
                "benchmark_return_percent",
            ],
            0.0,
        )
    )

    excess_return = safe_float(
        extract_metric(
            raw_window,
            [
                "excess_return",
                "excess_return_percent",
            ],
            strategy_return - default_return,
        )
    )

    sharpe_ratio = safe_float(
        extract_metric(
            raw_window,
            [
                "sharpe_ratio",
                "validation_sharpe",
                "strategy_sharpe",
            ],
            0.0,
        )
    )

    default_sharpe = safe_float(
        extract_metric(
            raw_window,
            [
                "default_sharpe",
                "default_sharpe_ratio",
                "benchmark_sharpe",
            ],
            0.0,
        )
    )

    maximum_drawdown = safe_float(
        extract_metric(
            raw_window,
            [
                "maximum_drawdown",
                "maximum_drawdown_percent",
                "drawdown",
                "drawdown_percent",
            ],
            0.0,
        )
    )

    profit_factor = safe_float(
        extract_metric(
            raw_window,
            [
                "profit_factor",
            ],
            0.0,
        )
    )

    win_rate = safe_float(
        extract_metric(
            raw_window,
            [
                "win_rate",
                "win_rate_percent",
            ],
            0.0,
        )
    )

    total_trades = safe_int(
        extract_metric(
            raw_window,
            [
                "total_trades",
                "trades",
                "completed_trades",
            ],
            0,
        )
    )

    return_retention = safe_float(
        extract_metric(
            raw_window,
            [
                "return_retention",
                "return_retention_percent",
            ],
            0.0,
        )
    )

    sharpe_retention = safe_float(
        extract_metric(
            raw_window,
            [
                "sharpe_retention",
                "sharpe_retention_percent",
            ],
            0.0,
        )
    )

    if (
        return_retention == 0.0
        and strategy_return != 0.0
    ):
        training_return = safe_float(
            extract_metric(
                raw_window,
                [
                    "training_return",
                    "training_return_percent",
                ],
                0.0,
            )
        )

        if training_return != 0:
            return_retention = (
                strategy_return
                / training_return
                * 100.0
            )

    if (
        sharpe_retention == 0.0
        and sharpe_ratio != 0.0
    ):
        training_sharpe = safe_float(
            extract_metric(
                raw_window,
                [
                    "training_sharpe",
                    "training_sharpe_ratio",
                ],
                0.0,
            )
        )

        if training_sharpe != 0:
            sharpe_retention = (
                sharpe_ratio
                / training_sharpe
                * 100.0
            )

    return_score = calculate_return_score(
        strategy_return=strategy_return,
        default_return=default_return,
    )

    sharpe_score = calculate_sharpe_score(
        sharpe_ratio=sharpe_ratio,
        default_sharpe=default_sharpe,
    )

    drawdown_score = calculate_drawdown_score(
        drawdown_percent=maximum_drawdown
    )

    profit_factor_score = (
        calculate_profit_factor_score(
            profit_factor=profit_factor
        )
    )

    consistency_score = 0.0

    if return_retention >= 50.0:
        consistency_score += 50.0

    elif return_retention >= 25.0:
        consistency_score += 30.0

    elif return_retention > 0:
        consistency_score += 15.0

    if sharpe_retention >= 50.0:
        consistency_score += 50.0

    elif sharpe_retention >= 25.0:
        consistency_score += 30.0

    elif sharpe_retention > 0:
        consistency_score += 15.0

    diagnostic_score = clamp_score(
        return_score * 0.30
        + sharpe_score * 0.25
        + drawdown_score * 0.20
        + profit_factor_score * 0.15
        + consistency_score * 0.10
    )

    diagnostic_status = determine_window_status(
        diagnostic_score=diagnostic_score,
        strategy_return=strategy_return,
        sharpe_ratio=sharpe_ratio,
        profit_factor=profit_factor,
    )

    profitable = (
        strategy_return > 0
    )

    beat_default_return = (
        strategy_return
        > default_return
    )

    beat_default_sharpe = (
        sharpe_ratio
        > default_sharpe
    )

    acceptable = (
        diagnostic_status
        in {
            "ROBUST",
            "ACCEPTABLE",
        }
    )

    problems: list[str] = []
    strengths: list[str] = []

    if not profitable:
        problems.append(
            "검증 구간 전략 수익률이 0% 이하입니다."
        )

    else:
        strengths.append(
            "검증 구간에서 플러스 수익을 기록했습니다."
        )

    if not beat_default_return:
        problems.append(
            "전략 수익률이 기본 전략 수익률보다 낮습니다."
        )

    else:
        strengths.append(
            "기본 전략 수익률을 초과했습니다."
        )

    if sharpe_ratio < 0.5:
        problems.append(
            "Sharpe Ratio가 0.50 미만입니다."
        )

    elif sharpe_ratio >= 1.0:
        strengths.append(
            "Sharpe Ratio가 1.00 이상입니다."
        )

    if not beat_default_sharpe:
        problems.append(
            "전략 Sharpe Ratio가 기본 전략보다 낮습니다."
        )

    if abs(
        maximum_drawdown
    ) > 10.0:
        problems.append(
            "최대 낙폭이 10%를 초과했습니다."
        )

    elif abs(
        maximum_drawdown
    ) <= 7.5:
        strengths.append(
            "최대 낙폭이 비교적 안정적입니다."
        )

    if profit_factor < 1.1:
        problems.append(
            "Profit Factor가 1.10 미만입니다."
        )

    elif profit_factor >= 1.3:
        strengths.append(
            "Profit Factor가 1.30 이상입니다."
        )

    if total_trades < 15:
        problems.append(
            "거래 횟수가 적어 통계적 신뢰도가 낮을 수 있습니다."
        )

    if (
        return_retention > 0
        and return_retention < 20.0
    ):
        problems.append(
            "훈련 대비 검증 수익 유지율이 매우 낮습니다."
        )

    if (
        sharpe_retention > 0
        and sharpe_retention < 30.0
    ):
        problems.append(
            "훈련 대비 검증 Sharpe 유지율이 낮습니다."
        )

    return WalkForwardWindowDiagnostic(
        window_number=window_number,

        training_start=training_start,
        training_end=training_end,

        validation_start=validation_start,
        validation_end=validation_end,

        entry_score=round(
            entry_score,
            2,
        ),

        exit_score=round(
            exit_score,
            2,
        ),

        stop_atr_multiple=round(
            stop_atr_multiple,
            2,
        ),

        target_atr_multiple=round(
            target_atr_multiple,
            2,
        ),

        maximum_holding_days=(
            maximum_holding_days
        ),

        position_percent=round(
            position_percent,
            2,
        ),

        strategy_return_percent=round(
            strategy_return,
            2,
        ),

        default_return_percent=round(
            default_return,
            2,
        ),

        excess_return_percent=round(
            excess_return,
            2,
        ),

        sharpe_ratio=round(
            sharpe_ratio,
            2,
        ),

        default_sharpe_ratio=round(
            default_sharpe,
            2,
        ),

        maximum_drawdown_percent=round(
            maximum_drawdown,
            2,
        ),

        profit_factor=round(
            profit_factor,
            2,
        ),

        win_rate_percent=round(
            win_rate,
            2,
        ),

        total_trades=total_trades,

        return_retention_percent=round(
            return_retention,
            2,
        ),

        sharpe_retention_percent=round(
            sharpe_retention,
            2,
        ),

        return_score=return_score,
        sharpe_score=sharpe_score,
        drawdown_score=drawdown_score,
        profit_factor_score=profit_factor_score,

        consistency_score=clamp_score(
            consistency_score
        ),

        diagnostic_score=diagnostic_score,
        diagnostic_status=diagnostic_status,

        profitable=profitable,

        beat_default_return=(
            beat_default_return
        ),

        beat_default_sharpe=(
            beat_default_sharpe
        ),

        acceptable=acceptable,

        problems=problems,
        strengths=strengths,
    )


def calculate_parameter_stability(
    windows: list[
        WalkForwardWindowDiagnostic
    ],
) -> float:
    """
    구간별 파라미터 안정성을 계산합니다.
    """

    if not windows:
        return 0.0

    parameter_groups = [
        [
            window.entry_score
            for window in windows
        ],
        [
            window.exit_score
            for window in windows
        ],
        [
            window.stop_atr_multiple
            for window in windows
        ],
        [
            window.target_atr_multiple
            for window in windows
        ],
        [
            window.maximum_holding_days
            for window in windows
        ],
    ]

    stability_scores: list[float] = []

    for values in parameter_groups:
        if not values:
            continue

        common = mode_value(
            values
        )

        matching = sum(
            1
            for value in values
            if value == common
        )

        stability_scores.append(
            matching
            / len(values)
            * 100.0
        )

    return safe_average(
        stability_scores
    )


def calculate_performance_consistency(
    windows: list[
        WalkForwardWindowDiagnostic
    ],
) -> float:
    """
    검증 구간별 성과 일관성을 계산합니다.
    """

    if not windows:
        return 0.0

    profitable_percent = safe_percent(
        sum(
            1
            for window in windows
            if window.profitable
        ),
        len(windows),
    )

    acceptable_percent = safe_percent(
        sum(
            1
            for window in windows
            if window.acceptable
        ),
        len(windows),
    )

    positive_sharpe_percent = safe_percent(
        sum(
            1
            for window in windows
            if window.sharpe_ratio > 0
        ),
        len(windows),
    )

    controlled_drawdown_percent = safe_percent(
        sum(
            1
            for window in windows
            if abs(
                window.maximum_drawdown_percent
            ) <= 10.0
        ),
        len(windows),
    )

    return clamp_score(
        profitable_percent * 0.35
        + acceptable_percent * 0.30
        + positive_sharpe_percent * 0.20
        + controlled_drawdown_percent * 0.15
    )


def calculate_recent_performance_score(
    windows: list[
        WalkForwardWindowDiagnostic
    ],
) -> tuple[
    float,
    str,
]:
    """
    최근 검증 구간 성능과 과거 성능을 비교합니다.
    """

    if not windows:
        return (
            0.0,
            "UNKNOWN",
        )

    if len(windows) == 1:
        return (
            windows[0].diagnostic_score,
            "STABLE",
        )

    split_index = max(
        1,
        len(windows) // 2,
    )

    older_windows = windows[
        :split_index
    ]

    recent_windows = windows[
        split_index:
    ]

    older_score = safe_average(
        [
            window.diagnostic_score
            for window in older_windows
        ]
    )

    recent_score = safe_average(
        [
            window.diagnostic_score
            for window in recent_windows
        ]
    )

    score_difference = (
        recent_score
        - older_score
    )

    if score_difference >= 10.0:
        trend = "IMPROVING"

    elif score_difference <= -10.0:
        trend = "DETERIORATING"

    else:
        trend = "STABLE"

    adjusted_score = recent_score

    if trend == "IMPROVING":
        adjusted_score += 5.0

    elif trend == "DETERIORATING":
        adjusted_score -= 10.0

    return (
        clamp_score(
            adjusted_score
        ),
        trend,
    )


def determine_overall_status(
    overall_score: float,
    profitable_percent: float,
    acceptable_percent: float,
    recent_trend: str,
) -> str:
    """
    Walk-Forward 전체 상태를 결정합니다.
    """

    if (
        overall_score >= 80.0
        and profitable_percent >= 80.0
        and acceptable_percent >= 70.0
        and recent_trend != "DETERIORATING"
    ):
        return "ROBUST"

    if (
        overall_score >= 60.0
        and profitable_percent >= 60.0
        and acceptable_percent >= 50.0
    ):
        return "ACCEPTABLE"

    if (
        overall_score >= 40.0
        and profitable_percent >= 40.0
    ):
        return "WEAK"

    return "FAILED"


def build_diagnostic_notes(
    windows: list[
        WalkForwardWindowDiagnostic
    ],
    parameter_stability_score: float,
    performance_consistency_score: float,
    recent_trend: str,
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    전체 문제점, 강점 및 개선 권장사항을 생성합니다.
    """

    critical_problems: list[str] = []
    strengths: list[str] = []
    recommendations: list[str] = []

    total_windows = len(
        windows
    )

    profitable_windows = sum(
        1
        for window in windows
        if window.profitable
    )

    acceptable_windows = sum(
        1
        for window in windows
        if window.acceptable
    )

    beat_default_windows = sum(
        1
        for window in windows
        if window.beat_default_return
    )

    profitable_percent = safe_percent(
        profitable_windows,
        total_windows,
    )

    acceptable_percent = safe_percent(
        acceptable_windows,
        total_windows,
    )

    beat_default_percent = safe_percent(
        beat_default_windows,
        total_windows,
    )

    if profitable_percent < 60.0:
        critical_problems.append(
            "수익을 기록한 Walk-Forward 검증 구간이 "
            "60% 미만입니다."
        )

        recommendations.append(
            "진입 점수를 높이거나 시장 추세 필터를 추가해 "
            "약한 신호를 줄이세요."
        )

    else:
        strengths.append(
            "대부분의 Walk-Forward 검증 구간에서 "
            "플러스 수익을 유지했습니다."
        )

    if acceptable_percent < 50.0:
        critical_problems.append(
            "최소 품질 기준을 통과한 검증 구간이 "
            "절반 미만입니다."
        )

        recommendations.append(
            "단일 최적 파라미터보다 여러 구간에서 반복적으로 "
            "선택된 공통 파라미터를 우선 사용하세요."
        )

    if beat_default_percent < 50.0:
        critical_problems.append(
            "기본 전략 수익률을 초과한 검증 구간이 "
            "절반 미만입니다."
        )

        recommendations.append(
            "전략 목표를 절대수익뿐 아니라 Buy-and-Hold 대비 "
            "초과수익 기준으로 다시 최적화하세요."
        )

    if parameter_stability_score < 60.0:
        critical_problems.append(
            "검증 구간별 선택 파라미터의 안정성이 낮습니다."
        )

        recommendations.append(
            "파라미터 검색 범위를 줄이고 인접 값들의 평균 성능이 "
            "좋은 영역을 선택하세요."
        )

    else:
        strengths.append(
            "구간별 전략 파라미터가 비교적 안정적입니다."
        )

    if performance_consistency_score < 60.0:
        critical_problems.append(
            "Walk-Forward 구간별 성과 편차가 큽니다."
        )

        recommendations.append(
            "상승장, 하락장, 횡보장을 구분하는 시장 상태 필터를 "
            "전략에 추가하세요."
        )

    else:
        strengths.append(
            "검증 구간별 성과 일관성이 비교적 양호합니다."
        )

    if recent_trend == "DETERIORATING":
        critical_problems.append(
            "최근 Walk-Forward 검증 성과가 과거보다 악화됐습니다."
        )

        recommendations.append(
            "최근 2~3년 데이터의 가중치를 높이고 오래된 데이터의 "
            "영향을 줄이는 재학습 방식을 검토하세요."
        )

    elif recent_trend == "IMPROVING":
        strengths.append(
            "최근 Walk-Forward 검증 성과가 개선되는 추세입니다."
        )

    else:
        strengths.append(
            "최근 Walk-Forward 검증 성과가 급격히 "
            "악화되지는 않았습니다."
        )

    low_trade_windows = [
        window.window_number
        for window in windows
        if window.total_trades < 15
    ]

    if low_trade_windows:
        critical_problems.append(
            "일부 검증 구간의 거래 횟수가 부족합니다: "
            + ", ".join(
                str(number)
                for number in low_trade_windows
            )
        )

        recommendations.append(
            "검증 기간을 늘리거나 거래 빈도가 너무 낮은 "
            "파라미터 조합을 제외하세요."
        )

    negative_windows = [
        window.window_number
        for window in windows
        if not window.profitable
    ]

    if negative_windows:
        recommendations.append(
            "손실 구간의 시장 상태와 기술지표를 별도로 분석하세요. "
            f"대상 구간: {negative_windows}"
        )

    if not recommendations:
        recommendations.append(
            "현재 Walk-Forward 구조를 유지하면서 검증 구간을 "
            "추가해 반복 확인하세요."
        )

    return (
        critical_problems,
        strengths,
        recommendations,
    )


def run_walk_forward_diagnostic(
    symbol: str = "AAPL",
    source_file: str | Path | None = None,
) -> WalkForwardDiagnosticResult:
    """
    V7.4 Walk-Forward 결과를 읽어 상세 진단합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    started_at = datetime.now()

    print()
    print("=" * 130)
    print(
        f"{normalized_symbol} V8.1 "
        "WALK-FORWARD DIAGNOSTIC"
    )
    print("=" * 130)

    if source_file is None:
        source_path = (
            find_walk_forward_latest_file(
                normalized_symbol
            )
        )

    else:
        source_path = Path(
            source_file
        )

    print(
        f"Source file              : "
        f"{source_path}"
    )

    payload = load_walk_forward_result(
        source_path
    )

    raw_windows = extract_window_list(
        payload
    )

    print(
        f"Detected windows         : "
        f"{len(raw_windows)}"
    )

    print("=" * 130)

    windows: list[
        WalkForwardWindowDiagnostic
    ] = []

    failed_windows = 0

    for window_number, raw_window in enumerate(
        raw_windows,
        start=1,
    ):
        try:
            diagnostic = analyze_window(
                raw_window=raw_window,
                window_number=window_number,
            )

            windows.append(
                diagnostic
            )

            print(
                f"[{window_number}/{len(raw_windows)}] "
                f"{diagnostic.validation_start} "
                f"to {diagnostic.validation_end} | "
                f"Return "
                f"{diagnostic.strategy_return_percent:>7.2f}% | "
                f"Default "
                f"{diagnostic.default_return_percent:>7.2f}% | "
                f"Sharpe "
                f"{diagnostic.sharpe_ratio:>5.2f} | "
                f"DD "
                f"{diagnostic.maximum_drawdown_percent:>7.2f}% | "
                f"Score "
                f"{diagnostic.diagnostic_score:>6.2f} | "
                f"{diagnostic.diagnostic_status}"
            )

        except Exception as error:
            failed_windows += 1

            print(
                f"[{window_number}/{len(raw_windows)}] "
                f"FAILED: "
                f"{type(error).__name__} - {error}"
            )

    if not windows:
        raise RuntimeError(
            "분석에 성공한 Walk-Forward 구간이 없습니다."
        )

    profitable_windows = sum(
        1
        for window in windows
        if window.profitable
    )

    acceptable_windows = sum(
        1
        for window in windows
        if window.acceptable
    )

    beat_default_return_windows = sum(
        1
        for window in windows
        if window.beat_default_return
    )

    beat_default_sharpe_windows = sum(
        1
        for window in windows
        if window.beat_default_sharpe
    )

    strategy_returns = [
        window.strategy_return_percent
        for window in windows
    ]

    default_returns = [
        window.default_return_percent
        for window in windows
    ]

    excess_returns = [
        window.excess_return_percent
        for window in windows
    ]

    sharpe_values = [
        window.sharpe_ratio
        for window in windows
    ]

    drawdown_values = [
        window.maximum_drawdown_percent
        for window in windows
    ]

    profit_factors = [
        window.profit_factor
        for window in windows
    ]

    win_rates = [
        window.win_rate_percent
        for window in windows
    ]

    return_retentions = [
        window.return_retention_percent
        for window in windows
    ]

    sharpe_retentions = [
        window.sharpe_retention_percent
        for window in windows
    ]

    parameter_stability_score = (
        calculate_parameter_stability(
            windows
        )
    )

    performance_consistency_score = (
        calculate_performance_consistency(
            windows
        )
    )

    (
        recent_performance_score,
        recent_trend,
    ) = calculate_recent_performance_score(
        windows
    )

    average_window_score = safe_average(
        [
            window.diagnostic_score
            for window in windows
        ]
    )

    overall_diagnostic_score = clamp_score(
        average_window_score * 0.45
        + performance_consistency_score * 0.25
        + parameter_stability_score * 0.15
        + recent_performance_score * 0.15
    )

    profitable_percent = safe_percent(
        profitable_windows,
        len(windows),
    )

    acceptable_percent = safe_percent(
        acceptable_windows,
        len(windows),
    )

    beat_default_return_percent = (
        safe_percent(
            beat_default_return_windows,
            len(windows),
        )
    )

    beat_default_sharpe_percent = (
        safe_percent(
            beat_default_sharpe_windows,
            len(windows),
        )
    )

    validation_status = determine_overall_status(
        overall_score=(
            overall_diagnostic_score
        ),

        profitable_percent=(
            profitable_percent
        ),

        acceptable_percent=(
            acceptable_percent
        ),

        recent_trend=recent_trend,
    )

    (
        critical_problems,
        strengths,
        recommendations,
    ) = build_diagnostic_notes(
        windows=windows,

        parameter_stability_score=(
            parameter_stability_score
        ),

        performance_consistency_score=(
            performance_consistency_score
        ),

        recent_trend=recent_trend,
    )

    overfitting_warning = (
        validation_status
        in {
            "WEAK",
            "FAILED",
        }
        or parameter_stability_score < 60.0
        or performance_consistency_score < 60.0
        or recent_trend == "DETERIORATING"
        or beat_default_return_percent < 50.0
    )

    best_window = max(
        windows,
        key=lambda window: (
            window.diagnostic_score
        ),
    )

    worst_window = min(
        windows,
        key=lambda window: (
            window.diagnostic_score
        ),
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return WalkForwardDiagnosticResult(
        version="V8.1",
        symbol=normalized_symbol,

        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),

        elapsed_seconds=round(
            elapsed_seconds,
            2,
        ),

        source_file=str(
            source_path
        ),

        total_windows=len(
            raw_windows
        ),

        successful_windows=len(
            windows
        ),

        failed_windows=failed_windows,

        profitable_windows=(
            profitable_windows
        ),

        profitable_percent=(
            profitable_percent
        ),

        acceptable_windows=(
            acceptable_windows
        ),

        acceptable_percent=(
            acceptable_percent
        ),

        beat_default_return_windows=(
            beat_default_return_windows
        ),

        beat_default_return_percent=(
            beat_default_return_percent
        ),

        beat_default_sharpe_windows=(
            beat_default_sharpe_windows
        ),

        beat_default_sharpe_percent=(
            beat_default_sharpe_percent
        ),

        average_strategy_return_percent=(
            safe_average(
                strategy_returns
            )
        ),

        median_strategy_return_percent=(
            safe_median(
                strategy_returns
            )
        ),

        worst_strategy_return_percent=round(
            min(
                strategy_returns
            ),
            2,
        ),

        best_strategy_return_percent=round(
            max(
                strategy_returns
            ),
            2,
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

        average_sharpe_ratio=(
            safe_average(
                sharpe_values
            )
        ),

        median_sharpe_ratio=(
            safe_median(
                sharpe_values
            )
        ),

        worst_sharpe_ratio=round(
            min(
                sharpe_values
            ),
            2,
        ),

        best_sharpe_ratio=round(
            max(
                sharpe_values
            ),
            2,
        ),

        average_drawdown_percent=(
            safe_average(
                drawdown_values
            )
        ),

        worst_drawdown_percent=round(
            min(
                drawdown_values
            ),
            2,
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
            window.total_trades
            for window in windows
        ),

        average_return_retention_percent=(
            safe_average(
                return_retentions
            )
        ),

        average_sharpe_retention_percent=(
            safe_average(
                sharpe_retentions
            )
        ),

        parameter_stability_score=(
            parameter_stability_score
        ),

        performance_consistency_score=(
            performance_consistency_score
        ),

        recent_performance_score=(
            recent_performance_score
        ),

        overall_diagnostic_score=(
            overall_diagnostic_score
        ),

        validation_status=(
            validation_status
        ),

        recent_trend=recent_trend,

        overfitting_warning=(
            overfitting_warning
        ),

        best_window_number=(
            best_window.window_number
        ),

        worst_window_number=(
            worst_window.window_number
        ),

        most_common_entry_score=(
            mode_value(
                [
                    window.entry_score
                    for window in windows
                ]
            )
        ),

        most_common_exit_score=(
            mode_value(
                [
                    window.exit_score
                    for window in windows
                ]
            )
        ),

        most_common_stop_atr=(
            mode_value(
                [
                    window.stop_atr_multiple
                    for window in windows
                ]
            )
        ),

        most_common_target_atr=(
            mode_value(
                [
                    window.target_atr_multiple
                    for window in windows
                ]
            )
        ),

        most_common_holding_days=(
            mode_value(
                [
                    window.maximum_holding_days
                    for window in windows
                ]
            )
        ),

        critical_problems=(
            critical_problems
        ),

        strengths=strengths,

        recommendations=(
            recommendations
        ),

        windows=[
            window.to_dict()
            for window in windows
        ],
    )


def save_walk_forward_diagnostic(
    result: WalkForwardDiagnosticResult,
) -> tuple[
    Path,
    Path,
]:
    """
    V8.1 진단 결과를 JSON 파일로 저장합니다.
    """

    DIAGNOSTIC_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        DIAGNOSTIC_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_walk_forward_diagnostic_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        DIAGNOSTIC_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_walk_forward_diagnostic_"
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


def print_walk_forward_diagnostic(
    result: WalkForwardDiagnosticResult,
) -> None:
    """
    V8.1 진단 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 150)
    print(
        f"{result.symbol} V8.1 "
        "WALK-FORWARD DIAGNOSTIC RESULT"
    )
    print("=" * 150)

    print(
        f"Source file                   : "
        f"{result.source_file}"
    )

    print(
        f"Validation status             : "
        f"{result.validation_status}"
    )

    print(
        f"Overall diagnostic score      : "
        f"{result.overall_diagnostic_score:.2f}/100"
    )

    print(
        f"Overfitting warning           : "
        f"{result.overfitting_warning}"
    )

    print(
        f"Recent performance trend      : "
        f"{result.recent_trend}"
    )

    print()
    print("WINDOW SUMMARY")
    print("-" * 150)

    print(
        f"Total windows                 : "
        f"{result.total_windows}"
    )

    print(
        f"Successful windows            : "
        f"{result.successful_windows}"
    )

    print(
        f"Failed windows                : "
        f"{result.failed_windows}"
    )

    print(
        f"Profitable windows            : "
        f"{result.profitable_windows}/"
        f"{result.successful_windows} "
        f"({result.profitable_percent:.2f}%)"
    )

    print(
        f"Acceptable windows            : "
        f"{result.acceptable_windows}/"
        f"{result.successful_windows} "
        f"({result.acceptable_percent:.2f}%)"
    )

    print(
        f"Beat default return           : "
        f"{result.beat_default_return_windows}/"
        f"{result.successful_windows} "
        f"({result.beat_default_return_percent:.2f}%)"
    )

    print(
        f"Beat default Sharpe           : "
        f"{result.beat_default_sharpe_windows}/"
        f"{result.successful_windows} "
        f"({result.beat_default_sharpe_percent:.2f}%)"
    )

    print()
    print("RETURN PERFORMANCE")
    print("-" * 150)

    print(
        f"Average strategy return       : "
        f"{result.average_strategy_return_percent:.2f}%"
    )

    print(
        f"Median strategy return        : "
        f"{result.median_strategy_return_percent:.2f}%"
    )

    print(
        f"Best strategy return          : "
        f"{result.best_strategy_return_percent:.2f}%"
    )

    print(
        f"Worst strategy return         : "
        f"{result.worst_strategy_return_percent:.2f}%"
    )

    print(
        f"Average default return        : "
        f"{result.average_default_return_percent:.2f}%"
    )

    print(
        f"Average excess return         : "
        f"{result.average_excess_return_percent:.2f}%p"
    )

    print()
    print("RISK-ADJUSTED PERFORMANCE")
    print("-" * 150)

    print(
        f"Average Sharpe                : "
        f"{result.average_sharpe_ratio:.2f}"
    )

    print(
        f"Median Sharpe                 : "
        f"{result.median_sharpe_ratio:.2f}"
    )

    print(
        f"Best Sharpe                   : "
        f"{result.best_sharpe_ratio:.2f}"
    )

    print(
        f"Worst Sharpe                  : "
        f"{result.worst_sharpe_ratio:.2f}"
    )

    print(
        f"Average drawdown              : "
        f"{result.average_drawdown_percent:.2f}%"
    )

    print(
        f"Worst drawdown                : "
        f"{result.worst_drawdown_percent:.2f}%"
    )

    print(
        f"Average profit factor         : "
        f"{result.average_profit_factor:.2f}"
    )

    print(
        f"Average win rate              : "
        f"{result.average_win_rate_percent:.2f}%"
    )

    print(
        f"Total validation trades       : "
        f"{result.total_validation_trades}"
    )

    print()
    print("CONSISTENCY SCORES")
    print("-" * 150)

    print(
        f"Parameter stability           : "
        f"{result.parameter_stability_score:.2f}/100"
    )

    print(
        f"Performance consistency       : "
        f"{result.performance_consistency_score:.2f}/100"
    )

    print(
        f"Recent performance            : "
        f"{result.recent_performance_score:.2f}/100"
    )

    print(
        f"Return retention average      : "
        f"{result.average_return_retention_percent:.2f}%"
    )

    print(
        f"Sharpe retention average      : "
        f"{result.average_sharpe_retention_percent:.2f}%"
    )

    print()
    print("MOST COMMON PARAMETERS")
    print("-" * 150)

    print(
        f"Entry score                   : "
        f"{result.most_common_entry_score}"
    )

    print(
        f"Exit score                    : "
        f"{result.most_common_exit_score}"
    )

    print(
        f"Stop ATR                      : "
        f"{result.most_common_stop_atr}"
    )

    print(
        f"Target ATR                    : "
        f"{result.most_common_target_atr}"
    )

    print(
        f"Maximum holding days          : "
        f"{result.most_common_holding_days}"
    )

    print()
    print("WINDOW DETAIL")
    print("-" * 150)

    print(
        f"{'No.':<5}"
        f"{'Validation Period':<27}"
        f"{'Entry':>8}"
        f"{'Exit':>8}"
        f"{'Return':>10}"
        f"{'Default':>10}"
        f"{'Excess':>10}"
        f"{'Sharpe':>9}"
        f"{'DD':>9}"
        f"{'PF':>8}"
        f"{'Trades':>9}"
        f"{'Score':>9}"
        f"{'Status':>14}"
    )

    print("-" * 150)

    for window in result.windows:
        validation_period = (
            f"{window['validation_start']} "
            f"to {window['validation_end']}"
        )

        print(
            f"{window['window_number']:<5}"
            f"{validation_period:<27}"
            f"{float(window['entry_score']):>8.2f}"
            f"{float(window['exit_score']):>8.2f}"
            f"{float(window['strategy_return_percent']):>9.2f}%"
            f"{float(window['default_return_percent']):>9.2f}%"
            f"{float(window['excess_return_percent']):>9.2f}%p"
            f"{float(window['sharpe_ratio']):>9.2f}"
            f"{float(window['maximum_drawdown_percent']):>8.2f}%"
            f"{float(window['profit_factor']):>8.2f}"
            f"{int(window['total_trades']):>9}"
            f"{float(window['diagnostic_score']):>9.2f}"
            f"{str(window['diagnostic_status']):>14}"
        )

    print()
    print(
        f"Best window                  : "
        f"{result.best_window_number}"
    )

    print(
        f"Worst window                 : "
        f"{result.worst_window_number}"
    )

    if result.critical_problems:
        print()
        print("CRITICAL PROBLEMS")
        print("-" * 150)

        for problem in result.critical_problems:
            print(
                f"- {problem}"
            )

    if result.strengths:
        print()
        print("STRENGTHS")
        print("-" * 150)

        for strength in result.strengths:
            print(
                f"- {strength}"
            )

    if result.recommendations:
        print()
        print("RECOMMENDATIONS")
        print("-" * 150)

        for recommendation in result.recommendations:
            print(
                f"- {recommendation}"
            )

    print()
    print("FILES")
    print("-" * 150)

    print(
        f"Report file                   : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                   : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 150)

    print(
        "주의: 이 진단은 과거 Walk-Forward 검증 결과를 "
        "분석한 연구용 결과이며 실제 투자 조언이나 "
        "미래 수익 보장이 아닙니다."
    )