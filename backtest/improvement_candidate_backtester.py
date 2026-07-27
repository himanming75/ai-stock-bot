import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.recommendation_backtester import (
    run_recommendation_backtest,
)
from backtest.walk_forward_validator import (
    run_walk_forward_validation,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

IMPROVEMENT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "walk_forward_improvement"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "improvement_candidate_backtest"
)


@dataclass
class CandidateBacktestResult:
    """
    하나의 V8.2 개선 후보를 실제 백테스트와
    Walk-Forward 방식으로 검증한 결과입니다.
    """

    rank: int

    source_candidate_number: int
    candidate_name: str
    candidate_type: str
    recommendation_status: str
    generator_priority_score: float

    entry_score: float
    exit_score: float
    stop_atr_multiple: float
    target_atr_multiple: float
    maximum_holding_days: int
    position_percent: float

    backtest_success: bool
    walk_forward_success: bool

    strategy_return_percent: float
    buy_and_hold_return_percent: float
    excess_return_percent: float

    sharpe_ratio: float
    maximum_drawdown_percent: float
    profit_factor: float
    win_rate_percent: float
    total_trades: int

    walk_forward_status: str
    walk_forward_score: float
    profitable_windows_percent: float
    acceptable_windows_percent: float
    beat_default_return_percent: float
    parameter_stability_score: float

    return_score: float
    sharpe_score: float
    drawdown_score: float
    profit_factor_score: float
    walk_forward_component_score: float
    trade_quality_score: float

    final_score: float
    final_status: str

    passed_minimum_trades: bool
    passed_drawdown_limit: bool
    passed_profit_factor: bool
    passed_sharpe: bool
    passed_walk_forward: bool
    passed_all_checks: bool

    error_message: str | None

    reasons: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ImprovementCandidateBacktestReport:
    """
    V8.3 Improvement Candidate Backtester 전체 결과입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    source_file: str

    requested_candidates: int
    tested_candidates: int
    successful_candidates: int
    failed_candidates: int

    passed_candidates: int
    rejected_candidates: int

    baseline_tested: bool
    baseline_final_score: float

    winner_candidate_number: int | None
    winner_candidate_name: str | None
    winner_candidate_type: str | None
    winner_final_score: float
    winner_status: str | None

    winner_entry_score: float | None
    winner_exit_score: float | None
    winner_stop_atr: float | None
    winner_target_atr: float | None
    winner_holding_days: int | None
    winner_position_percent: float | None

    winner_strategy_return_percent: float
    winner_sharpe_ratio: float
    winner_drawdown_percent: float
    winner_profit_factor: float
    winner_total_trades: int

    improvement_over_baseline_score: float

    candidates: list[dict[str, Any]]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정규화합니다.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
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
    값을 안전하게 bool로 변환합니다.
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
    value: float,
) -> float:
    """
    점수를 0~100 범위로 제한합니다.
    """

    return round(
        max(
            0.0,
            min(
                100.0,
                value,
            ),
        ),
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


def object_to_dict(
    value: Any,
) -> dict[str, Any]:
    """
    Dataclass, 일반 객체 또는 Dictionary를
    Dictionary 형식으로 변환합니다.
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if is_dataclass(value):
        converted = asdict(value)

        if isinstance(converted, dict):
            return converted

    to_dict_method = getattr(
        value,
        "to_dict",
        None,
    )

    if callable(to_dict_method):
        converted = to_dict_method()

        if isinstance(converted, dict):
            return converted

    if hasattr(
        value,
        "__dict__",
    ):
        converted = vars(value)

        if isinstance(converted, dict):
            return converted

    return {}


def recursive_find_value(
    data: Any,
    candidate_keys: list[str],
    default: Any = None,
) -> Any:
    """
    중첩 Dictionary와 List 전체를 검색하여
    후보 키 중 첫 값을 찾습니다.
    """

    normalized_keys = {
        key.lower()
        for key in candidate_keys
    }

    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in normalized_keys:
                if value is not None:
                    return value

        for value in data.values():
            found = recursive_find_value(
                value,
                candidate_keys,
                None,
            )

            if found is not None:
                return found

    elif isinstance(data, list):
        for item in data:
            found = recursive_find_value(
                item,
                candidate_keys,
                None,
            )

            if found is not None:
                return found

    return default


def find_latest_improvement_file(
    symbol: str,
) -> Path:
    """
    V8.2 Improvement latest JSON 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    expected_path = (
        IMPROVEMENT_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "walk_forward_improvement_latest.json"
        )
    )

    if expected_path.exists():
        return expected_path

    if not IMPROVEMENT_DIRECTORY.exists():
        raise FileNotFoundError(
            "Walk-Forward Improvement 폴더가 없습니다: "
            f"{IMPROVEMENT_DIRECTORY}"
        )

    candidates = [
        path
        for path in IMPROVEMENT_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "walk_forward_improvement_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not candidates:
        raise FileNotFoundError(
            f"{normalized_symbol} V8.2 Improvement "
            "결과 파일을 찾을 수 없습니다."
        )

    return max(
        candidates,
        key=lambda path: path.stat().st_mtime,
    )


def load_improvement_file(
    source_path: Path,
) -> dict[str, Any]:
    """
    V8.2 후보 JSON을 읽습니다.
    """

    if not source_path.exists():
        raise FileNotFoundError(
            f"후보 파일이 없습니다: {source_path}"
        )

    with source_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            "V8.2 Improvement JSON의 최상위 값이 "
            "객체 형식이 아닙니다."
        )

    candidates = payload.get(
        "candidates"
    )

    if not isinstance(
        candidates,
        list,
    ):
        raise ValueError(
            "V8.2 Improvement JSON에 "
            "candidates 목록이 없습니다."
        )

    return payload


def calculate_return_score(
    strategy_return: float,
) -> float:
    """
    전략 수익률 점수를 계산합니다.
    """

    if strategy_return >= 100.0:
        return 100.0

    if strategy_return >= 60.0:
        return 90.0

    if strategy_return >= 30.0:
        return 80.0

    if strategy_return >= 15.0:
        return 70.0

    if strategy_return >= 5.0:
        return 60.0

    if strategy_return > 0.0:
        return 50.0

    if strategy_return > -5.0:
        return 30.0

    return 10.0


def calculate_sharpe_score(
    sharpe_ratio: float,
) -> float:
    """
    Sharpe Ratio 점수를 계산합니다.
    """

    if sharpe_ratio >= 2.0:
        return 100.0

    if sharpe_ratio >= 1.5:
        return 90.0

    if sharpe_ratio >= 1.0:
        return 80.0

    if sharpe_ratio >= 0.7:
        return 70.0

    if sharpe_ratio >= 0.5:
        return 60.0

    if sharpe_ratio > 0.0:
        return 40.0

    return 10.0


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
        return 90.0

    if absolute_drawdown <= 10.0:
        return 80.0

    if absolute_drawdown <= 12.5:
        return 70.0

    if absolute_drawdown <= 15.0:
        return 60.0

    if absolute_drawdown <= 20.0:
        return 40.0

    return 10.0


def calculate_profit_factor_score(
    profit_factor: float,
) -> float:
    """
    Profit Factor 점수를 계산합니다.
    """

    if profit_factor >= 2.0:
        return 100.0

    if profit_factor >= 1.7:
        return 90.0

    if profit_factor >= 1.5:
        return 80.0

    if profit_factor >= 1.3:
        return 70.0

    if profit_factor >= 1.1:
        return 60.0

    if profit_factor >= 1.0:
        return 45.0

    return 10.0


def calculate_trade_quality_score(
    total_trades: int,
    win_rate_percent: float,
) -> float:
    """
    거래 수와 승률을 이용하여 거래 품질 점수를 계산합니다.
    """

    trade_count_score = 0.0

    if total_trades >= 100:
        trade_count_score = 100.0

    elif total_trades >= 60:
        trade_count_score = 85.0

    elif total_trades >= 30:
        trade_count_score = 70.0

    elif total_trades >= 15:
        trade_count_score = 50.0

    elif total_trades > 0:
        trade_count_score = 25.0

    win_rate_score = 0.0

    if win_rate_percent >= 60.0:
        win_rate_score = 100.0

    elif win_rate_percent >= 55.0:
        win_rate_score = 85.0

    elif win_rate_percent >= 50.0:
        win_rate_score = 70.0

    elif win_rate_percent >= 45.0:
        win_rate_score = 55.0

    elif win_rate_percent > 0:
        win_rate_score = 35.0

    return clamp_score(
        trade_count_score * 0.60
        + win_rate_score * 0.40
    )


def calculate_walk_forward_score(
    validation_status: str,
    profitable_windows_percent: float,
    acceptable_windows_percent: float,
    beat_default_return_percent: float,
    parameter_stability_score: float,
) -> float:
    """
    Walk-Forward 검증 결과 점수를 계산합니다.
    """

    status_score_map = {
        "ROBUST": 100.0,
        "ACCEPTABLE": 75.0,
        "WEAK": 40.0,
        "FAILED": 10.0,
        "UNKNOWN": 20.0,
    }

    status_score = status_score_map.get(
        validation_status.upper(),
        20.0,
    )

    return clamp_score(
        status_score * 0.35
        + profitable_windows_percent * 0.20
        + acceptable_windows_percent * 0.20
        + beat_default_return_percent * 0.15
        + parameter_stability_score * 0.10
    )


def determine_final_status(
    final_score: float,
    passed_all_checks: bool,
) -> str:
    """
    최종 후보 상태를 결정합니다.
    """

    if (
        final_score >= 80.0
        and passed_all_checks
    ):
        return "ROBUST"

    if (
        final_score >= 65.0
        and passed_all_checks
    ):
        return "ACCEPTABLE"

    if final_score >= 50.0:
        return "WEAK"

    return "REJECTED"


def extract_backtest_metrics(
    raw_result: Any,
) -> dict[str, Any]:
    """
    Recommendation Backtest 결과에서
    주요 성과 지표를 추출합니다.
    """

    data = object_to_dict(
        raw_result
    )

    strategy_return = safe_float(
        recursive_find_value(
            data,
            [
                "strategy_return",
                "strategy_return_percent",
                "return_percent",
                "total_return",
                "total_return_percent",
            ],
            0.0,
        )
    )

    buy_and_hold_return = safe_float(
        recursive_find_value(
            data,
            [
                "buy_and_hold_return",
                "buy_and_hold_return_percent",
                "buy_hold_return",
                "buyhold_return",
                "benchmark_return",
            ],
            0.0,
        )
    )

    excess_return = safe_float(
        recursive_find_value(
            data,
            [
                "excess_return",
                "excess_return_percent",
            ],
            (
                strategy_return
                - buy_and_hold_return
            ),
        )
    )

    sharpe_ratio = safe_float(
        recursive_find_value(
            data,
            [
                "sharpe_ratio",
                "sharpe",
            ],
            0.0,
        )
    )

    maximum_drawdown = safe_float(
        recursive_find_value(
            data,
            [
                "maximum_drawdown",
                "maximum_drawdown_percent",
                "max_drawdown",
                "drawdown",
            ],
            0.0,
        )
    )

    profit_factor = safe_float(
        recursive_find_value(
            data,
            [
                "profit_factor",
            ],
            0.0,
        )
    )

    win_rate = safe_float(
        recursive_find_value(
            data,
            [
                "win_rate",
                "win_rate_percent",
            ],
            0.0,
        )
    )

    total_trades = safe_int(
        recursive_find_value(
            data,
            [
                "total_trades",
                "completed_trades",
                "trades",
            ],
            0,
        )
    )

    return {
        "strategy_return_percent": round(
            strategy_return,
            2,
        ),
        "buy_and_hold_return_percent": round(
            buy_and_hold_return,
            2,
        ),
        "excess_return_percent": round(
            excess_return,
            2,
        ),
        "sharpe_ratio": round(
            sharpe_ratio,
            2,
        ),
        "maximum_drawdown_percent": round(
            maximum_drawdown,
            2,
        ),
        "profit_factor": round(
            profit_factor,
            2,
        ),
        "win_rate_percent": round(
            win_rate,
            2,
        ),
        "total_trades": total_trades,
    }


def extract_walk_forward_metrics(
    raw_result: Any,
) -> dict[str, Any]:
    """
    Walk-Forward 결과에서 주요 검증 지표를 추출합니다.
    """

    data = object_to_dict(
        raw_result
    )

    validation_status = str(
        recursive_find_value(
            data,
            [
                "validation_status",
                "overall_status",
                "status",
            ],
            "UNKNOWN",
        )
    ).upper()

    overall_score = safe_float(
        recursive_find_value(
            data,
            [
                "overall_score",
                "walk_forward_score",
                "validation_score",
                "final_score",
            ],
            0.0,
        )
    )

    profitable_windows_percent = safe_float(
        recursive_find_value(
            data,
            [
                "profitable_windows_percent",
                "profitable_percent",
            ],
            0.0,
        )
    )

    acceptable_windows_percent = safe_float(
        recursive_find_value(
            data,
            [
                "acceptable_windows_percent",
                "acceptable_percent",
            ],
            0.0,
        )
    )

    beat_default_return_percent = safe_float(
        recursive_find_value(
            data,
            [
                "beat_default_return_percent",
                "beat_default_percent",
            ],
            0.0,
        )
    )

    parameter_stability_score = safe_float(
        recursive_find_value(
            data,
            [
                "parameter_stability_score",
                "parameter_stability",
            ],
            0.0,
        )
    )

    total_windows = safe_int(
        recursive_find_value(
            data,
            [
                "total_windows",
            ],
            0,
        )
    )

    profitable_windows = safe_int(
        recursive_find_value(
            data,
            [
                "profitable_windows",
            ],
            0,
        )
    )

    acceptable_windows = safe_int(
        recursive_find_value(
            data,
            [
                "acceptable_windows",
            ],
            0,
        )
    )

    beat_default_windows = safe_int(
        recursive_find_value(
            data,
            [
                "beat_default_return_windows",
                "beat_default_windows",
            ],
            0,
        )
    )

    if (
        profitable_windows_percent == 0.0
        and total_windows > 0
    ):
        profitable_windows_percent = (
            safe_percent(
                profitable_windows,
                total_windows,
            )
        )

    if (
        acceptable_windows_percent == 0.0
        and total_windows > 0
    ):
        acceptable_windows_percent = (
            safe_percent(
                acceptable_windows,
                total_windows,
            )
        )

    if (
        beat_default_return_percent == 0.0
        and total_windows > 0
    ):
        beat_default_return_percent = (
            safe_percent(
                beat_default_windows,
                total_windows,
            )
        )

    calculated_score = (
        calculate_walk_forward_score(
            validation_status=validation_status,
            profitable_windows_percent=(
                profitable_windows_percent
            ),
            acceptable_windows_percent=(
                acceptable_windows_percent
            ),
            beat_default_return_percent=(
                beat_default_return_percent
            ),
            parameter_stability_score=(
                parameter_stability_score
            ),
        )
    )

    if overall_score <= 0:
        overall_score = calculated_score

    return {
        "validation_status": (
            validation_status
        ),
        "walk_forward_score": clamp_score(
            overall_score
        ),
        "profitable_windows_percent": round(
            profitable_windows_percent,
            2,
        ),
        "acceptable_windows_percent": round(
            acceptable_windows_percent,
            2,
        ),
        "beat_default_return_percent": round(
            beat_default_return_percent,
            2,
        ),
        "parameter_stability_score": round(
            parameter_stability_score,
            2,
        ),
    }


def build_candidate_notes(
    strategy_return: float,
    sharpe_ratio: float,
    drawdown_percent: float,
    profit_factor: float,
    total_trades: int,
    walk_forward_status: str,
    passed_all_checks: bool,
) -> tuple[list[str], list[str]]:
    """
    후보 평가 이유와 경고를 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if strategy_return > 0:
        reasons.append(
            "전체 백테스트에서 플러스 수익을 기록했습니다."
        )

    else:
        warnings.append(
            "전체 백테스트 수익률이 0% 이하입니다."
        )

    if sharpe_ratio >= 1.0:
        reasons.append(
            "Sharpe Ratio가 1.00 이상입니다."
        )

    elif sharpe_ratio < 0.5:
        warnings.append(
            "Sharpe Ratio가 0.50 미만입니다."
        )

    if abs(drawdown_percent) <= 10.0:
        reasons.append(
            "최대 낙폭이 10% 이내입니다."
        )

    else:
        warnings.append(
            "최대 낙폭이 10%를 초과했습니다."
        )

    if profit_factor >= 1.3:
        reasons.append(
            "Profit Factor가 1.30 이상입니다."
        )

    elif profit_factor < 1.1:
        warnings.append(
            "Profit Factor가 1.10 미만입니다."
        )

    if total_trades >= 30:
        reasons.append(
            "거래 횟수가 최소 통계 기준을 충족했습니다."
        )

    else:
        warnings.append(
            "거래 횟수가 30회 미만입니다."
        )

    if walk_forward_status in {
        "ROBUST",
        "ACCEPTABLE",
    }:
        reasons.append(
            "Walk-Forward 검증 상태가 최소 기준을 "
            "통과했습니다."
        )

    else:
        warnings.append(
            "Walk-Forward 검증 상태가 약하거나 "
            "실패 상태입니다."
        )

    if passed_all_checks:
        reasons.append(
            "모든 최소 품질 검사를 통과했습니다."
        )

    return (
        reasons,
        warnings,
    )


def test_single_candidate(
    symbol: str,
    candidate: dict[str, Any],
    period: str,
    interval: str,
    initial_cash: float,
    commission_per_trade: float,
    training_years: float,
    validation_years: float,
    step_years: float,
    estimated_trading_days_per_year: int,
    minimum_trades: int,
    maximum_drawdown_limit: float,
) -> CandidateBacktestResult:
    """
    하나의 개선 후보를 전체 백테스트와
    Walk-Forward 검증으로 평가합니다.
    """

    source_candidate_number = safe_int(
        candidate.get(
            "candidate_number",
            0,
        )
    )

    candidate_name = str(
        candidate.get(
            "candidate_name",
            (
                f"CANDIDATE_"
                f"{source_candidate_number}"
            ),
        )
    )

    candidate_type = str(
        candidate.get(
            "candidate_type",
            "UNKNOWN",
        )
    ).upper()

    recommendation_status = str(
        candidate.get(
            "recommendation_status",
            "UNKNOWN",
        )
    ).upper()

    generator_priority_score = safe_float(
        candidate.get(
            "priority_score",
            0.0,
        )
    )

    entry_score = safe_float(
        candidate.get(
            "entry_score",
            64.0,
        )
    )

    exit_score = safe_float(
        candidate.get(
            "exit_score",
            42.0,
        )
    )

    stop_atr = safe_float(
        candidate.get(
            "stop_atr_multiple",
            1.50,
        )
    )

    target_atr = safe_float(
        candidate.get(
            "target_atr_multiple",
            2.50,
        )
    )

    maximum_holding_days = safe_int(
        candidate.get(
            "maximum_holding_days",
            20,
        )
    )

    position_percent = safe_float(
        candidate.get(
            "position_percent",
            20.0,
        )
    )

    backtest_success = False
    walk_forward_success = False

    error_messages: list[str] = []

    backtest_metrics = {
        "strategy_return_percent": 0.0,
        "buy_and_hold_return_percent": 0.0,
        "excess_return_percent": 0.0,
        "sharpe_ratio": 0.0,
        "maximum_drawdown_percent": 0.0,
        "profit_factor": 0.0,
        "win_rate_percent": 0.0,
        "total_trades": 0,
    }

    walk_forward_metrics = {
        "validation_status": "FAILED",
        "walk_forward_score": 0.0,
        "profitable_windows_percent": 0.0,
        "acceptable_windows_percent": 0.0,
        "beat_default_return_percent": 0.0,
        "parameter_stability_score": 0.0,
    }

    try:
        raw_backtest = run_recommendation_backtest(
            symbol=symbol,
            period=period,
            interval=interval,
            initial_cash=initial_cash,
            position_percent=position_percent,
            entry_score=entry_score,
            exit_score=exit_score,
            stop_atr_multiple=stop_atr,
            target_atr_multiple=target_atr,
            maximum_holding_days=(
                maximum_holding_days
            ),
            commission_per_trade=(
                commission_per_trade
            ),
        )

        backtest_metrics = (
            extract_backtest_metrics(
                raw_backtest
            )
        )

        backtest_success = True

    except Exception as error:
        error_messages.append(
            "Backtest: "
            f"{type(error).__name__} - {error}"
        )

    try:
        raw_walk_forward = (
            run_walk_forward_validation(
                symbol=symbol,
                period=period,
                interval=interval,

                training_years=training_years,
                validation_years=validation_years,
                step_years=step_years,

                estimated_trading_days_per_year=(
                    estimated_trading_days_per_year
                ),

                initial_cash=initial_cash,

                commission_per_trade=(
                    commission_per_trade
                ),

                entry_scores=[
                    entry_score
                ],

                exit_scores=[
                    exit_score
                ],

                stop_atr_multiples=[
                    stop_atr
                ],

                target_atr_multiples=[
                    target_atr
                ],

                maximum_holding_days_list=[
                    maximum_holding_days
                ],

                position_percents=[
                    position_percent
                ],

                minimum_training_trades=(
                    minimum_trades
                ),

                minimum_validation_trades=10,

                top_n=1,
            )
        )

        walk_forward_metrics = (
            extract_walk_forward_metrics(
                raw_walk_forward
            )
        )

        walk_forward_success = True

    except Exception as error:
        error_messages.append(
            "Walk-Forward: "
            f"{type(error).__name__} - {error}"
        )

    strategy_return = safe_float(
        backtest_metrics[
            "strategy_return_percent"
        ]
    )

    buy_and_hold_return = safe_float(
        backtest_metrics[
            "buy_and_hold_return_percent"
        ]
    )

    excess_return = safe_float(
        backtest_metrics[
            "excess_return_percent"
        ]
    )

    sharpe_ratio = safe_float(
        backtest_metrics[
            "sharpe_ratio"
        ]
    )

    drawdown_percent = safe_float(
        backtest_metrics[
            "maximum_drawdown_percent"
        ]
    )

    profit_factor = safe_float(
        backtest_metrics[
            "profit_factor"
        ]
    )

    win_rate = safe_float(
        backtest_metrics[
            "win_rate_percent"
        ]
    )

    total_trades = safe_int(
        backtest_metrics[
            "total_trades"
        ]
    )

    walk_forward_status = str(
        walk_forward_metrics[
            "validation_status"
        ]
    ).upper()

    walk_forward_score = safe_float(
        walk_forward_metrics[
            "walk_forward_score"
        ]
    )

    profitable_windows_percent = safe_float(
        walk_forward_metrics[
            "profitable_windows_percent"
        ]
    )

    acceptable_windows_percent = safe_float(
        walk_forward_metrics[
            "acceptable_windows_percent"
        ]
    )

    beat_default_return_percent = safe_float(
        walk_forward_metrics[
            "beat_default_return_percent"
        ]
    )

    parameter_stability_score = safe_float(
        walk_forward_metrics[
            "parameter_stability_score"
        ]
    )

    return_score = calculate_return_score(
        strategy_return
    )

    sharpe_score = calculate_sharpe_score(
        sharpe_ratio
    )

    drawdown_score = calculate_drawdown_score(
        drawdown_percent
    )

    profit_factor_score = (
        calculate_profit_factor_score(
            profit_factor
        )
    )

    trade_quality_score = (
        calculate_trade_quality_score(
            total_trades=total_trades,
            win_rate_percent=win_rate,
        )
    )

    walk_forward_component_score = (
        calculate_walk_forward_score(
            validation_status=(
                walk_forward_status
            ),

            profitable_windows_percent=(
                profitable_windows_percent
            ),

            acceptable_windows_percent=(
                acceptable_windows_percent
            ),

            beat_default_return_percent=(
                beat_default_return_percent
            ),

            parameter_stability_score=(
                parameter_stability_score
            ),
        )
    )

    passed_minimum_trades = (
        total_trades >= minimum_trades
    )

    passed_drawdown_limit = (
        abs(drawdown_percent)
        <= maximum_drawdown_limit
    )

    passed_profit_factor = (
        profit_factor >= 1.10
    )

    passed_sharpe = (
        sharpe_ratio >= 0.50
    )

    passed_walk_forward = (
        walk_forward_success
        and walk_forward_status
        in {
            "ROBUST",
            "ACCEPTABLE",
        }
    )

    passed_all_checks = all(
        [
            backtest_success,
            walk_forward_success,
            passed_minimum_trades,
            passed_drawdown_limit,
            passed_profit_factor,
            passed_sharpe,
            passed_walk_forward,
        ]
    )

    final_score = clamp_score(
        return_score * 0.15
        + sharpe_score * 0.20
        + drawdown_score * 0.15
        + profit_factor_score * 0.15
        + trade_quality_score * 0.10
        + walk_forward_component_score * 0.25
    )

    if not backtest_success:
        final_score = 0.0

    elif not walk_forward_success:
        final_score = clamp_score(
            final_score - 25.0
        )

    if not passed_minimum_trades:
        final_score = clamp_score(
            final_score - 10.0
        )

    if not passed_drawdown_limit:
        final_score = clamp_score(
            final_score - 10.0
        )

    if not passed_profit_factor:
        final_score = clamp_score(
            final_score - 10.0
        )

    final_status = determine_final_status(
        final_score=final_score,
        passed_all_checks=passed_all_checks,
    )

    (
        reasons,
        warnings,
    ) = build_candidate_notes(
        strategy_return=strategy_return,
        sharpe_ratio=sharpe_ratio,
        drawdown_percent=drawdown_percent,
        profit_factor=profit_factor,
        total_trades=total_trades,
        walk_forward_status=(
            walk_forward_status
        ),
        passed_all_checks=(
            passed_all_checks
        ),
    )

    return CandidateBacktestResult(
        rank=0,

        source_candidate_number=(
            source_candidate_number
        ),

        candidate_name=candidate_name,
        candidate_type=candidate_type,

        recommendation_status=(
            recommendation_status
        ),

        generator_priority_score=round(
            generator_priority_score,
            2,
        ),

        entry_score=round(
            entry_score,
            2,
        ),

        exit_score=round(
            exit_score,
            2,
        ),

        stop_atr_multiple=round(
            stop_atr,
            2,
        ),

        target_atr_multiple=round(
            target_atr,
            2,
        ),

        maximum_holding_days=(
            maximum_holding_days
        ),

        position_percent=round(
            position_percent,
            2,
        ),

        backtest_success=(
            backtest_success
        ),

        walk_forward_success=(
            walk_forward_success
        ),

        strategy_return_percent=round(
            strategy_return,
            2,
        ),

        buy_and_hold_return_percent=round(
            buy_and_hold_return,
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

        maximum_drawdown_percent=round(
            drawdown_percent,
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

        walk_forward_status=(
            walk_forward_status
        ),

        walk_forward_score=round(
            walk_forward_score,
            2,
        ),

        profitable_windows_percent=round(
            profitable_windows_percent,
            2,
        ),

        acceptable_windows_percent=round(
            acceptable_windows_percent,
            2,
        ),

        beat_default_return_percent=round(
            beat_default_return_percent,
            2,
        ),

        parameter_stability_score=round(
            parameter_stability_score,
            2,
        ),

        return_score=round(
            return_score,
            2,
        ),

        sharpe_score=round(
            sharpe_score,
            2,
        ),

        drawdown_score=round(
            drawdown_score,
            2,
        ),

        profit_factor_score=round(
            profit_factor_score,
            2,
        ),

        walk_forward_component_score=round(
            walk_forward_component_score,
            2,
        ),

        trade_quality_score=round(
            trade_quality_score,
            2,
        ),

        final_score=round(
            final_score,
            2,
        ),

        final_status=final_status,

        passed_minimum_trades=(
            passed_minimum_trades
        ),

        passed_drawdown_limit=(
            passed_drawdown_limit
        ),

        passed_profit_factor=(
            passed_profit_factor
        ),

        passed_sharpe=passed_sharpe,

        passed_walk_forward=(
            passed_walk_forward
        ),

        passed_all_checks=(
            passed_all_checks
        ),

        error_message=(
            " | ".join(error_messages)
            if error_messages
            else None
        ),

        reasons=reasons,
        warnings=warnings,
    )


def run_improvement_candidate_backtest(
    symbol: str = "AAPL",
    source_file: str | Path | None = None,

    maximum_candidates: int = 10,

    period: str = "10y",
    interval: str = "1d",

    initial_cash: float = 10000.0,
    commission_per_trade: float = 0.0,

    training_years: float = 4.0,
    validation_years: float = 1.0,
    step_years: float = 1.0,

    estimated_trading_days_per_year: int = 252,

    minimum_trades: int = 30,
    maximum_drawdown_limit: float = 15.0,
) -> ImprovementCandidateBacktestReport:
    """
    V8.2에서 생성한 상위 후보를 실제 백테스트와
    Walk-Forward 검증으로 비교합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if maximum_candidates <= 0:
        raise ValueError(
            "maximum_candidates는 1 이상이어야 합니다."
        )

    started_at = datetime.now()

    print()
    print("=" * 150)
    print(
        f"{normalized_symbol} V8.3 "
        "IMPROVEMENT CANDIDATE BACKTESTER"
    )
    print("=" * 150)

    if source_file is None:
        source_path = (
            find_latest_improvement_file(
                normalized_symbol
            )
        )

    else:
        source_path = Path(
            source_file
        )

    payload = load_improvement_file(
        source_path
    )

    raw_candidates = payload.get(
        "candidates",
        [],
    )

    selected_candidates = [
        candidate
        for candidate in raw_candidates[
            :maximum_candidates
        ]
        if isinstance(candidate, dict)
    ]

    if not selected_candidates:
        raise RuntimeError(
            "테스트할 개선 후보가 없습니다."
        )

    print(
        f"Source file             : "
        f"{source_path}"
    )

    print(
        f"Available candidates    : "
        f"{len(raw_candidates)}"
    )

    print(
        f"Selected candidates     : "
        f"{len(selected_candidates)}"
    )

    print(
        f"Period                  : "
        f"{period}"
    )

    print(
        f"Training / Validation   : "
        f"{training_years:.1f}y / "
        f"{validation_years:.1f}y"
    )

    print(
        f"Minimum trades          : "
        f"{minimum_trades}"
    )

    print(
        f"Maximum drawdown limit  : "
        f"{maximum_drawdown_limit:.2f}%"
    )

    print("=" * 150)

    baseline_candidate = {
        "candidate_number": 0,
        "candidate_name": "BASELINE_REFERENCE",
        "candidate_type": "BASELINE",
        "recommendation_status": "REFERENCE",
        "priority_score": 0.0,

        "entry_score": safe_float(
            payload.get(
                "base_entry_score",
                64.0,
            )
        ),

        "exit_score": safe_float(
            payload.get(
                "base_exit_score",
                42.0,
            )
        ),

        "stop_atr_multiple": safe_float(
            payload.get(
                "base_stop_atr",
                1.50,
            )
        ),

        "target_atr_multiple": safe_float(
            payload.get(
                "base_target_atr",
                2.50,
            )
        ),

        "maximum_holding_days": safe_int(
            payload.get(
                "base_holding_days",
                20,
            )
        ),

        "position_percent": safe_float(
            payload.get(
                "base_position_percent",
                20.0,
            )
        ),
    }

    print()
    print("#" * 150)
    print("BASELINE REFERENCE")
    print("#" * 150)

    baseline_result = test_single_candidate(
        symbol=normalized_symbol,
        candidate=baseline_candidate,

        period=period,
        interval=interval,

        initial_cash=initial_cash,

        commission_per_trade=(
            commission_per_trade
        ),

        training_years=training_years,
        validation_years=validation_years,
        step_years=step_years,

        estimated_trading_days_per_year=(
            estimated_trading_days_per_year
        ),

        minimum_trades=minimum_trades,

        maximum_drawdown_limit=(
            maximum_drawdown_limit
        ),
    )

    print(
        f"Baseline completed      : "
        f"Score "
        f"{baseline_result.final_score:.2f}/100 | "
        f"Return "
        f"{baseline_result.strategy_return_percent:.2f}% | "
        f"Sharpe "
        f"{baseline_result.sharpe_ratio:.2f} | "
        f"WF "
        f"{baseline_result.walk_forward_status}"
    )

    tested_results: list[
        CandidateBacktestResult
    ] = []

    for index, candidate in enumerate(
        selected_candidates,
        start=1,
    ):
        print()
        print("#" * 150)

        print(
            f"[{index}/{len(selected_candidates)}] "
            f"{candidate.get('candidate_name')}"
        )

        print("#" * 150)

        result = test_single_candidate(
            symbol=normalized_symbol,
            candidate=candidate,

            period=period,
            interval=interval,

            initial_cash=initial_cash,

            commission_per_trade=(
                commission_per_trade
            ),

            training_years=training_years,
            validation_years=validation_years,
            step_years=step_years,

            estimated_trading_days_per_year=(
                estimated_trading_days_per_year
            ),

            minimum_trades=minimum_trades,

            maximum_drawdown_limit=(
                maximum_drawdown_limit
            ),
        )

        tested_results.append(
            result
        )

        print(
            f"{result.candidate_name} completed: "
            f"Score {result.final_score:.2f}/100 | "
            f"Return "
            f"{result.strategy_return_percent:.2f}% | "
            f"Sharpe {result.sharpe_ratio:.2f} | "
            f"DD "
            f"{result.maximum_drawdown_percent:.2f}% | "
            f"PF {result.profit_factor:.2f} | "
            f"WF {result.walk_forward_status} | "
            f"{result.final_status}"
        )

        if result.error_message:
            print(
                f"Warning: {result.error_message}"
            )

    tested_results.sort(
        key=lambda item: (
            item.passed_all_checks,
            item.final_score,
            item.walk_forward_component_score,
            item.sharpe_ratio,
            item.strategy_return_percent,
            -abs(
                item.maximum_drawdown_percent
            ),
        ),
        reverse=True,
    )

    for rank, candidate_result in enumerate(
        tested_results,
        start=1,
    ):
        candidate_result.rank = rank

    successful_candidates = sum(
        1
        for result in tested_results
        if (
            result.backtest_success
            and result.walk_forward_success
        )
    )

    failed_candidates = (
        len(tested_results)
        - successful_candidates
    )

    passed_candidates = sum(
        1
        for result in tested_results
        if result.passed_all_checks
    )

    rejected_candidates = (
        len(tested_results)
        - passed_candidates
    )

    winner = (
        tested_results[0]
        if tested_results
        else None
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    winner_score = (
        winner.final_score
        if winner
        else 0.0
    )

    improvement_over_baseline = round(
        winner_score
        - baseline_result.final_score,
        2,
    )

    report = ImprovementCandidateBacktestReport(
        version="V8.3",
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

        requested_candidates=(
            maximum_candidates
        ),

        tested_candidates=len(
            tested_results
        ),

        successful_candidates=(
            successful_candidates
        ),

        failed_candidates=(
            failed_candidates
        ),

        passed_candidates=(
            passed_candidates
        ),

        rejected_candidates=(
            rejected_candidates
        ),

        baseline_tested=True,

        baseline_final_score=round(
            baseline_result.final_score,
            2,
        ),

        winner_candidate_number=(
            winner.source_candidate_number
            if winner
            else None
        ),

        winner_candidate_name=(
            winner.candidate_name
            if winner
            else None
        ),

        winner_candidate_type=(
            winner.candidate_type
            if winner
            else None
        ),

        winner_final_score=round(
            winner_score,
            2,
        ),

        winner_status=(
            winner.final_status
            if winner
            else None
        ),

        winner_entry_score=(
            winner.entry_score
            if winner
            else None
        ),

        winner_exit_score=(
            winner.exit_score
            if winner
            else None
        ),

        winner_stop_atr=(
            winner.stop_atr_multiple
            if winner
            else None
        ),

        winner_target_atr=(
            winner.target_atr_multiple
            if winner
            else None
        ),

        winner_holding_days=(
            winner.maximum_holding_days
            if winner
            else None
        ),

        winner_position_percent=(
            winner.position_percent
            if winner
            else None
        ),

        winner_strategy_return_percent=(
            winner.strategy_return_percent
            if winner
            else 0.0
        ),

        winner_sharpe_ratio=(
            winner.sharpe_ratio
            if winner
            else 0.0
        ),

        winner_drawdown_percent=(
            winner.maximum_drawdown_percent
            if winner
            else 0.0
        ),

        winner_profit_factor=(
            winner.profit_factor
            if winner
            else 0.0
        ),

        winner_total_trades=(
            winner.total_trades
            if winner
            else 0
        ),

        improvement_over_baseline_score=(
            improvement_over_baseline
        ),

        candidates=[
            result.to_dict()
            for result in tested_results
        ],
    )

    print_improvement_candidate_backtest(
        report
    )

    return report


def save_improvement_candidate_backtest(
    report: ImprovementCandidateBacktestReport,
) -> tuple[Path, Path]:
    """
    V8.3 결과를 JSON으로 저장합니다.
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
            f"{report.symbol}_"
            "improvement_candidate_backtest_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{report.symbol}_"
            "improvement_candidate_backtest_latest.json"
        )
    )

    report.report_path = str(
        report_path
    )

    report.latest_path = str(
        latest_path
    )

    payload = report.to_dict()

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


def print_improvement_candidate_backtest(
    report: ImprovementCandidateBacktestReport,
) -> None:
    """
    V8.3 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 160)
    print(
        f"{report.symbol} V8.3 "
        "IMPROVEMENT CANDIDATE BACKTEST RESULT"
    )
    print("=" * 160)

    print(
        f"Source file                    : "
        f"{report.source_file}"
    )

    print(
        f"Tested candidates              : "
        f"{report.tested_candidates}"
    )

    print(
        f"Successful candidates          : "
        f"{report.successful_candidates}"
    )

    print(
        f"Failed candidates              : "
        f"{report.failed_candidates}"
    )

    print(
        f"Passed candidates              : "
        f"{report.passed_candidates}"
    )

    print(
        f"Rejected candidates            : "
        f"{report.rejected_candidates}"
    )

    print(
        f"Baseline score                 : "
        f"{report.baseline_final_score:.2f}/100"
    )

    print()
    print("FINAL RANKING")
    print("-" * 160)

    print(
        f"{'Rank':<6}"
        f"{'Candidate':<31}"
        f"{'Type':<15}"
        f"{'Return':>10}"
        f"{'Sharpe':>9}"
        f"{'DD':>9}"
        f"{'PF':>8}"
        f"{'Trades':>9}"
        f"{'WF':>13}"
        f"{'WF Score':>10}"
        f"{'Final':>9}"
        f"{'Status':>14}"
        f"{'Passed':>9}"
    )

    print("-" * 160)

    for candidate in report.candidates:
        print(
            f"{int(candidate['rank']):<6}"
            f"{str(candidate['candidate_name']):<31}"
            f"{str(candidate['candidate_type']):<15}"
            f"{float(candidate['strategy_return_percent']):>9.2f}%"
            f"{float(candidate['sharpe_ratio']):>9.2f}"
            f"{float(candidate['maximum_drawdown_percent']):>8.2f}%"
            f"{float(candidate['profit_factor']):>8.2f}"
            f"{int(candidate['total_trades']):>9}"
            f"{str(candidate['walk_forward_status']):>13}"
            f"{float(candidate['walk_forward_component_score']):>10.2f}"
            f"{float(candidate['final_score']):>9.2f}"
            f"{str(candidate['final_status']):>14}"
            f"{str(candidate['passed_all_checks']):>9}"
        )

    print()
    print("WINNER")
    print("-" * 160)

    print(
        f"Candidate number               : "
        f"{report.winner_candidate_number}"
    )

    print(
        f"Candidate name                 : "
        f"{report.winner_candidate_name}"
    )

    print(
        f"Candidate type                 : "
        f"{report.winner_candidate_type}"
    )

    print(
        f"Final score                    : "
        f"{report.winner_final_score:.2f}/100"
    )

    print(
        f"Final status                   : "
        f"{report.winner_status}"
    )

    print(
        f"Improvement over baseline      : "
        f"{report.improvement_over_baseline_score:+.2f} points"
    )

    print()
    print("WINNER PARAMETERS")
    print("-" * 160)

    print(
        f"Entry score                    : "
        f"{report.winner_entry_score}"
    )

    print(
        f"Exit score                     : "
        f"{report.winner_exit_score}"
    )

    print(
        f"Stop ATR                       : "
        f"{report.winner_stop_atr}"
    )

    print(
        f"Target ATR                     : "
        f"{report.winner_target_atr}"
    )

    print(
        f"Maximum holding days           : "
        f"{report.winner_holding_days}"
    )

    print(
        f"Position percent               : "
        f"{report.winner_position_percent}%"
    )

    print()
    print("WINNER PERFORMANCE")
    print("-" * 160)

    print(
        f"Strategy return                : "
        f"{report.winner_strategy_return_percent:.2f}%"
    )

    print(
        f"Sharpe ratio                   : "
        f"{report.winner_sharpe_ratio:.2f}"
    )

    print(
        f"Maximum drawdown               : "
        f"{report.winner_drawdown_percent:.2f}%"
    )

    print(
        f"Profit factor                  : "
        f"{report.winner_profit_factor:.2f}"
    )

    print(
        f"Total trades                   : "
        f"{report.winner_total_trades}"
    )

    print()
    print("FILES")
    print("-" * 160)

    print(
        f"Report file                    : "
        f"{report.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                    : "
        f"{report.latest_path or 'Not saved yet'}"
    )

    print("=" * 160)

    print(
        "주의: 이 결과는 과거 데이터 기반 백테스트 및 "
        "Walk-Forward 시뮬레이션이며 실제 주문 체결이나 "
        "미래 수익을 보장하지 않습니다."
    )