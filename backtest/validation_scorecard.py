import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

STRATEGY_BACKTEST_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
)

SCORECARD_OUTPUT_DIRECTORY = (
    STRATEGY_BACKTEST_DIRECTORY
    / "validation_scorecard"
)


VALIDATION_WEIGHTS = {
    "out_of_sample": 15.0,
    "walk_forward": 20.0,
    "parameter_robustness": 15.0,
    "multi_period_robustness": 15.0,
    "trading_cost_stress": 10.0,
    "realistic_execution": 10.0,
    "execution_consistency": 15.0,
}


@dataclass
class ValidationComponent:
    """
    한 가지 검증 항목의 평가 결과입니다.
    """

    component_key: str
    component_name: str
    version: str

    weight: float
    raw_score: float
    weighted_score: float

    status: str
    passed: bool
    warning: bool

    source_file: str | None

    metrics: dict[str, Any]
    reasons: list[str]
    warnings: list[str]

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyValidationScorecard:
    """
    V8.0 전체 전략 검증 점수표입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    total_components: int
    loaded_components: int
    missing_components: int
    failed_components: int

    total_weight: float
    earned_weighted_score: float
    final_score: float

    passed_components: int
    warning_components: int

    validation_status: str
    deployment_readiness: str

    critical_failure: bool
    overfitting_warning: bool

    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]

    components: list[dict[str, Any]]

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
    여러 형태의 값을 bool로 변환합니다.
    """

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        normalized = (
            value
            .strip()
            .lower()
        )

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


def first_value(
    data: dict[str, Any],
    keys: list[str],
    default: Any = None,
) -> Any:
    """
    여러 후보 키 중 처음 발견된 값을 반환합니다.
    """

    for key in keys:
        if (
            key in data
            and data[key] is not None
        ):
            return data[key]

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


def normalize_status(
    status: Any,
) -> str:
    """
    상태 문자열을 대문자로 정규화합니다.
    """

    return str(
        status
        or "UNKNOWN"
    ).strip().upper()


def load_json_file(
    path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽습니다.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"검증 결과 파일이 없습니다: {path}"
        )

    with path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(
            file
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            f"JSON 최상위 데이터가 객체가 아닙니다: {path}"
        )

    return payload


def find_latest_file(
    directory_name: str,
    symbol: str,
    preferred_names: list[str],
) -> Path | None:
    """
    우선 지정된 latest 파일을 찾고,
    없으면 폴더 안의 가장 최근 JSON 파일을 찾습니다.
    """

    directory = (
        STRATEGY_BACKTEST_DIRECTORY
        / directory_name
    )

    for filename in preferred_names:
        candidate = (
            directory
            / filename
        )

        if candidate.exists():
            return candidate

    if not directory.exists():
        return None

    json_files = [
        path
        for path in directory.glob(
            f"{symbol}_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not json_files:
        return None

    return max(
        json_files,
        key=lambda path: path.stat().st_mtime,
    )


def score_status_value(
    status: str,
) -> float:
    """
    공통 검증 상태를 기본 점수로 변환합니다.
    """

    status_scores = {
        "ROBUST": 100.0,
        "STRONG": 95.0,
        "ACCEPTABLE": 80.0,
        "PASS": 80.0,
        "PASSED": 80.0,
        "EXPERIMENTAL": 65.0,
        "WEAK": 45.0,
        "COST_SENSITIVE": 40.0,
        "RESEARCH_ONLY": 35.0,
        "UNPROFITABLE": 20.0,
        "FAILED": 0.0,
        "ERROR": 0.0,
        "UNKNOWN": 30.0,
    }

    return status_scores.get(
        status,
        50.0,
    )


def calculate_out_of_sample_component(
    data: dict[str, Any],
    source_file: Path,
) -> ValidationComponent:
    """
    V7.3 Out-of-Sample 결과를 평가합니다.
    """

    status = normalize_status(
        first_value(
            data,
            [
                "validation_status",
                "status",
            ],
        )
    )

    validation_return = safe_float(
        first_value(
            data,
            [
                "validation_return",
                "validation_return_percent",
                "strategy_return",
            ],
        )
    )

    validation_sharpe = safe_float(
        first_value(
            data,
            [
                "validation_sharpe",
                "validation_sharpe_ratio",
                "sharpe_ratio",
            ],
        )
    )

    validation_drawdown = safe_float(
        first_value(
            data,
            [
                "validation_drawdown",
                "validation_drawdown_percent",
                "maximum_drawdown_percent",
            ],
        )
    )

    return_retention = safe_float(
        first_value(
            data,
            [
                "return_retention",
                "return_retention_percent",
            ],
        )
    )

    profit_factor = safe_float(
        first_value(
            data,
            [
                "validation_profit_factor",
                "profit_factor",
            ],
        )
    )

    overfitting_warning = safe_bool(
        first_value(
            data,
            [
                "overfitting_warning",
            ],
            False,
        )
    )

    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    if validation_return > 0:
        score += 30.0

        reasons.append(
            "미사용 검증 구간에서 플러스 수익을 기록했습니다."
        )

    else:
        warnings.append(
            "미사용 검증 구간 수익률이 0% 이하입니다."
        )

    if validation_sharpe >= 1.0:
        score += 25.0

    elif validation_sharpe >= 0.5:
        score += 18.0

    elif validation_sharpe > 0:
        score += 8.0

    else:
        warnings.append(
            "검증 Sharpe Ratio가 0 이하입니다."
        )

    if abs(
        validation_drawdown
    ) <= 10.0:
        score += 20.0

    elif abs(
        validation_drawdown
    ) <= 15.0:
        score += 12.0

    elif abs(
        validation_drawdown
    ) <= 25.0:
        score += 5.0

    else:
        warnings.append(
            "검증 최대 낙폭이 25%를 초과했습니다."
        )

    if profit_factor >= 1.5:
        score += 15.0

    elif profit_factor >= 1.2:
        score += 10.0

    elif profit_factor >= 1.0:
        score += 5.0

    if return_retention >= 50.0:
        score += 10.0

    elif return_retention >= 20.0:
        score += 6.0

    elif return_retention > 0:
        score += 2.0

    if overfitting_warning:
        score -= 10.0

        warnings.append(
            "Out-of-Sample 결과에 과최적화 경고가 있습니다."
        )

    raw_score = clamp_score(
        score
    )

    weight = VALIDATION_WEIGHTS[
        "out_of_sample"
    ]

    weighted_score = round(
        raw_score
        * weight
        / 100.0,
        2,
    )

    passed = (
        status
        in {
            "ROBUST",
            "ACCEPTABLE",
            "PASS",
            "PASSED",
        }
        and validation_return > 0
    )

    return ValidationComponent(
        component_key="out_of_sample",
        component_name="Out-of-Sample Validation",
        version="V7.3",

        weight=weight,
        raw_score=raw_score,
        weighted_score=weighted_score,

        status=status,
        passed=passed,
        warning=overfitting_warning,

        source_file=str(
            source_file
        ),

        metrics={
            "validation_return_percent": validation_return,
            "validation_sharpe_ratio": validation_sharpe,
            "validation_drawdown_percent": validation_drawdown,
            "return_retention_percent": return_retention,
            "profit_factor": profit_factor,
        },

        reasons=reasons,
        warnings=warnings,
    )


def calculate_walk_forward_component(
    data: dict[str, Any],
    source_file: Path,
) -> ValidationComponent:
    """
    V7.4 Walk-Forward 결과를 평가합니다.
    """

    status = normalize_status(
        first_value(
            data,
            [
                "validation_status",
                "status",
            ],
        )
    )

    profitable_percent = safe_float(
        first_value(
            data,
            [
                "profitable_windows_percent",
                "profitable_percent",
            ],
        )
    )

    acceptable_percent = safe_float(
        first_value(
            data,
            [
                "acceptable_windows_percent",
                "acceptable_percent",
            ],
        )
    )

    beat_default_return = safe_float(
        first_value(
            data,
            [
                "beat_default_return_percent",
                "beat_default_return",
            ],
        )
    )

    average_return = safe_float(
        first_value(
            data,
            [
                "average_strategy_return",
                "average_validation_return",
            ],
        )
    )

    average_sharpe = safe_float(
        first_value(
            data,
            [
                "average_strategy_sharpe",
                "average_validation_sharpe",
            ],
        )
    )

    worst_drawdown = safe_float(
        first_value(
            data,
            [
                "worst_drawdown",
                "worst_drawdown_percent",
            ],
        )
    )

    parameter_stability = safe_float(
        first_value(
            data,
            [
                "parameter_stability",
                "parameter_stability_score",
            ],
        )
    )

    overfitting_warning = safe_bool(
        first_value(
            data,
            [
                "overfitting_warning",
            ],
            False,
        )
    )

    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    score += min(
        profitable_percent,
        100.0,
    ) * 0.25

    score += min(
        acceptable_percent,
        100.0,
    ) * 0.20

    score += min(
        beat_default_return,
        100.0,
    ) * 0.10

    score += min(
        parameter_stability,
        100.0,
    ) * 0.15

    if average_return > 0:
        score += 10.0

        reasons.append(
            "Walk-Forward 평균 검증 수익률이 플러스입니다."
        )

    if average_sharpe >= 1.0:
        score += 12.0

    elif average_sharpe >= 0.5:
        score += 8.0

    elif average_sharpe > 0:
        score += 3.0

    if abs(
        worst_drawdown
    ) <= 10.0:
        score += 8.0

    elif abs(
        worst_drawdown
    ) <= 15.0:
        score += 4.0

    if profitable_percent >= 70.0:
        reasons.append(
            "대부분의 Walk-Forward 검증 구간에서 수익을 냈습니다."
        )

    if parameter_stability >= 70.0:
        reasons.append(
            "검증 구간별 최적 파라미터가 비교적 안정적입니다."
        )

    if overfitting_warning:
        score -= 8.0

        warnings.append(
            "Walk-Forward 결과에 과최적화 경고가 있습니다."
        )

    raw_score = clamp_score(
        score
    )

    weight = VALIDATION_WEIGHTS[
        "walk_forward"
    ]

    return ValidationComponent(
        component_key="walk_forward",
        component_name="Walk-Forward Validation",
        version="V7.4",

        weight=weight,
        raw_score=raw_score,

        weighted_score=round(
            raw_score
            * weight
            / 100.0,
            2,
        ),

        status=status,

        passed=(
            status
            in {
                "ROBUST",
                "ACCEPTABLE",
                "PASS",
                "PASSED",
            }
            and profitable_percent >= 60.0
        ),

        warning=overfitting_warning,

        source_file=str(
            source_file
        ),

        metrics={
            "profitable_windows_percent": profitable_percent,
            "acceptable_windows_percent": acceptable_percent,
            "beat_default_return_percent": beat_default_return,
            "average_return_percent": average_return,
            "average_sharpe_ratio": average_sharpe,
            "worst_drawdown_percent": worst_drawdown,
            "parameter_stability_score": parameter_stability,
        },

        reasons=reasons,
        warnings=warnings,
    )


def calculate_parameter_robustness_component(
    data: dict[str, Any],
    source_file: Path,
) -> ValidationComponent:
    """
    V7.5 Parameter Robustness 결과를 평가합니다.
    """

    status = normalize_status(
        first_value(
            data,
            [
                "validation_status",
                "status",
            ],
        )
    )

    robustness_score = safe_float(
        first_value(
            data,
            [
                "robustness_score",
                "score",
            ],
        )
    )

    profitable_percent = safe_float(
        first_value(
            data,
            [
                "profitable_percent",
                "profitable_trials_percent",
            ],
        )
    )

    acceptable_percent = safe_float(
        first_value(
            data,
            [
                "acceptable_percent",
                "acceptable_trials_percent",
            ],
        )
    )

    nearby_robust_percent = safe_float(
        first_value(
            data,
            [
                "robust_nearby_percent",
                "robust_nearby_trials_percent",
            ],
        )
    )

    center_return_difference = safe_float(
        first_value(
            data,
            [
                "center_return_difference",
                "center_return_difference_percent",
            ],
        )
    )

    overfitting_warning = safe_bool(
        first_value(
            data,
            [
                "overfitting_warning",
            ],
            False,
        )
    )

    if robustness_score <= 0:
        robustness_score = (
            profitable_percent * 0.35
            + acceptable_percent * 0.35
            + nearby_robust_percent * 0.30
        )

    score = robustness_score
    reasons: list[str] = []
    warnings: list[str] = []

    if profitable_percent >= 80.0:
        reasons.append(
            "주변 파라미터 대부분이 플러스 수익을 기록했습니다."
        )

    if acceptable_percent >= 70.0:
        reasons.append(
            "주변 파라미터 대부분이 최소 품질 기준을 통과했습니다."
        )

    if abs(
        center_return_difference
    ) <= 5.0:
        score += 5.0

        reasons.append(
            "중심 파라미터와 주변 파라미터 성과 차이가 작습니다."
        )

    if overfitting_warning:
        score -= 10.0

        warnings.append(
            "파라미터 민감도 결과에 과최적화 경고가 있습니다."
        )

    raw_score = clamp_score(
        score
    )

    weight = VALIDATION_WEIGHTS[
        "parameter_robustness"
    ]

    return ValidationComponent(
        component_key="parameter_robustness",
        component_name="Parameter Robustness",
        version="V7.5",

        weight=weight,
        raw_score=raw_score,

        weighted_score=round(
            raw_score
            * weight
            / 100.0,
            2,
        ),

        status=status,

        passed=(
            status
            in {
                "ROBUST",
                "ACCEPTABLE",
            }
            and raw_score >= 65.0
        ),

        warning=overfitting_warning,

        source_file=str(
            source_file
        ),

        metrics={
            "robustness_score": robustness_score,
            "profitable_trials_percent": profitable_percent,
            "acceptable_trials_percent": acceptable_percent,
            "robust_nearby_percent": nearby_robust_percent,
            "center_return_difference_percent": center_return_difference,
        },

        reasons=reasons,
        warnings=warnings,
    )


def calculate_multi_period_component(
    data: dict[str, Any],
    source_file: Path,
) -> ValidationComponent:
    """
    V7.6 Multi-Period Robustness 결과를 평가합니다.
    """

    status = normalize_status(
        first_value(
            data,
            [
                "validation_status",
                "status",
            ],
        )
    )

    winner_score = safe_float(
        first_value(
            data,
            [
                "winner_score",
                "final_score",
            ],
        )
    )

    winner_strategy = str(
        first_value(
            data,
            [
                "winner_strategy",
                "selected_strategy",
            ],
            "N/A",
        )
    )

    overfitting_warning = safe_bool(
        first_value(
            data,
            [
                "overfitting_warning",
            ],
            False,
        )
    )

    total_tests = safe_int(
        first_value(
            data,
            [
                "total_tests",
            ],
        )
    )

    successful_tests = safe_int(
        first_value(
            data,
            [
                "successful_tests",
            ],
        )
    )

    failed_tests = safe_int(
        first_value(
            data,
            [
                "failed_tests",
            ],
        )
    )

    if winner_score <= 0:
        winner_score = score_status_value(
            status
        )

    success_percent = (
        successful_tests
        / total_tests
        * 100.0
        if total_tests > 0
        else 0.0
    )

    score = (
        winner_score * 0.80
        + success_percent * 0.20
    )

    reasons: list[str] = []
    warnings: list[str] = []

    if success_percent == 100.0:
        reasons.append(
            "모든 기간별 테스트가 오류 없이 완료됐습니다."
        )

    if winner_score >= 70.0:
        reasons.append(
            "선정 전략이 여러 기간에서 비교적 안정적인 점수를 기록했습니다."
        )

    if overfitting_warning:
        score -= 8.0

        warnings.append(
            "기간별 성과 편차로 과최적화 경고가 있습니다."
        )

    raw_score = clamp_score(
        score
    )

    weight = VALIDATION_WEIGHTS[
        "multi_period_robustness"
    ]

    return ValidationComponent(
        component_key="multi_period_robustness",
        component_name="Multi-Period Robustness",
        version="V7.6",

        weight=weight,
        raw_score=raw_score,

        weighted_score=round(
            raw_score
            * weight
            / 100.0,
            2,
        ),

        status=status,

        passed=(
            status
            in {
                "ROBUST",
                "ACCEPTABLE",
            }
            and failed_tests == 0
            and raw_score >= 60.0
        ),

        warning=overfitting_warning,

        source_file=str(
            source_file
        ),

        metrics={
            "winner_strategy": winner_strategy,
            "winner_score": winner_score,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_percent": round(
                success_percent,
                2,
            ),
        },

        reasons=reasons,
        warnings=warnings,
    )


def calculate_trading_cost_component(
    data: dict[str, Any],
    source_file: Path,
) -> ValidationComponent:
    """
    V7.7 Trading Cost Stress 결과를 평가합니다.
    """

    status = normalize_status(
        first_value(
            data,
            [
                "validation_status",
                "status",
            ],
        )
    )

    cost_robustness_score = safe_float(
        first_value(
            data,
            [
                "cost_robustness_score",
                "robustness_score",
            ],
        )
    )

    profitable_percent = safe_float(
        first_value(
            data,
            [
                "profitable_percent",
                "profitable_scenarios_percent",
            ],
        )
    )

    acceptable_percent = safe_float(
        first_value(
            data,
            [
                "acceptable_percent",
                "acceptable_scenarios_percent",
            ],
        )
    )

    worst_net_return = safe_float(
        first_value(
            data,
            [
                "worst_net_return",
                "worst_net_return_percent",
            ],
        )
    )

    worst_net_sharpe = safe_float(
        first_value(
            data,
            [
                "worst_net_sharpe",
                "worst_net_sharpe_ratio",
            ],
        )
    )

    maximum_return_reduction = safe_float(
        first_value(
            data,
            [
                "maximum_return_reduction",
                "maximum_return_reduction_percent",
            ],
        )
    )

    overfitting_warning = safe_bool(
        first_value(
            data,
            [
                "overfitting_warning",
            ],
            False,
        )
    )

    score = cost_robustness_score

    if score <= 0:
        score = (
            profitable_percent * 0.40
            + acceptable_percent * 0.30
        )

        if worst_net_return > 0:
            score += 15.0

        if worst_net_sharpe >= 0.5:
            score += 15.0

    reasons: list[str] = []
    warnings: list[str] = []

    if profitable_percent == 100.0:
        reasons.append(
            "모든 거래비용 조건에서 플러스 수익을 유지했습니다."
        )

    if worst_net_return > 0:
        reasons.append(
            "가장 높은 비용 조건에서도 수익이 플러스입니다."
        )

    if maximum_return_reduction > 30.0:
        warnings.append(
            "거래비용에 따른 최대 수익 감소 폭이 30%p를 초과했습니다."
        )

    if overfitting_warning:
        score -= 5.0

    raw_score = clamp_score(
        score
    )

    weight = VALIDATION_WEIGHTS[
        "trading_cost_stress"
    ]

    return ValidationComponent(
        component_key="trading_cost_stress",
        component_name="Trading Cost Stress",
        version="V7.7",

        weight=weight,
        raw_score=raw_score,

        weighted_score=round(
            raw_score
            * weight
            / 100.0,
            2,
        ),

        status=status,

        passed=(
            worst_net_return > 0
            and worst_net_sharpe >= 0.5
        ),

        warning=(
            overfitting_warning
            or maximum_return_reduction > 30.0
        ),

        source_file=str(
            source_file
        ),

        metrics={
            "cost_robustness_score": cost_robustness_score,
            "profitable_scenarios_percent": profitable_percent,
            "acceptable_scenarios_percent": acceptable_percent,
            "worst_net_return_percent": worst_net_return,
            "worst_net_sharpe_ratio": worst_net_sharpe,
            "maximum_return_reduction_percent": maximum_return_reduction,
        },

        reasons=reasons,
        warnings=warnings,
    )


def calculate_realistic_execution_component(
    data: dict[str, Any],
    source_file: Path,
) -> ValidationComponent:
    """
    V7.8 Realistic Execution 결과를 평가합니다.
    """

    success = safe_bool(
        first_value(
            data,
            [
                "success",
            ],
            True,
        )
    )

    net_return = safe_float(
        first_value(
            data,
            [
                "net_return_percent",
                "realistic_net_return",
            ],
        )
    )

    sharpe = safe_float(
        first_value(
            data,
            [
                "sharpe_ratio",
            ],
        )
    )

    drawdown = safe_float(
        first_value(
            data,
            [
                "maximum_drawdown_percent",
                "maximum_drawdown",
            ],
        )
    )

    profit_factor = safe_float(
        first_value(
            data,
            [
                "profit_factor",
            ],
        )
    )

    execution_cost = safe_float(
        first_value(
            data,
            [
                "total_execution_cost",
            ],
        )
    )

    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    if success:
        score += 10.0

    if net_return > 0:
        score += 30.0

        reasons.append(
            "현실 체결 조건에서도 순수익이 플러스입니다."
        )

    if sharpe >= 1.0:
        score += 25.0

    elif sharpe >= 0.5:
        score += 15.0

    if profit_factor >= 1.5:
        score += 20.0

    elif profit_factor >= 1.2:
        score += 12.0

    elif profit_factor >= 1.0:
        score += 5.0

    if abs(
        drawdown
    ) <= 10.0:
        score += 15.0

    elif abs(
        drawdown
    ) <= 15.0:
        score += 8.0

    if net_return <= 0:
        warnings.append(
            "현실 체결 조건의 순수익률이 0% 이하입니다."
        )

    raw_score = clamp_score(
        score
    )

    status = (
        "ROBUST"
        if raw_score >= 85.0
        else "ACCEPTABLE"
        if raw_score >= 65.0
        else "WEAK"
        if raw_score >= 45.0
        else "FAILED"
    )

    weight = VALIDATION_WEIGHTS[
        "realistic_execution"
    ]

    return ValidationComponent(
        component_key="realistic_execution",
        component_name="Realistic Execution",
        version="V7.8",

        weight=weight,
        raw_score=raw_score,

        weighted_score=round(
            raw_score
            * weight
            / 100.0,
            2,
        ),

        status=status,

        passed=(
            success
            and net_return > 0
            and sharpe >= 0.5
            and profit_factor >= 1.1
        ),

        warning=False,

        source_file=str(
            source_file
        ),

        metrics={
            "net_return_percent": net_return,
            "sharpe_ratio": sharpe,
            "maximum_drawdown_percent": drawdown,
            "profit_factor": profit_factor,
            "total_execution_cost": execution_cost,
        },

        reasons=reasons,
        warnings=warnings,
    )


def calculate_execution_consistency_component(
    data: dict[str, Any],
    source_file: Path,
) -> ValidationComponent:
    """
    V7.9 Execution Consistency 결과를 평가합니다.
    """

    status = normalize_status(
        first_value(
            data,
            [
                "validation_status",
                "status",
            ],
        )
    )

    consistency_score = safe_float(
        first_value(
            data,
            [
                "consistency_score",
                "score",
            ],
        )
    )

    path_consistency = safe_float(
        first_value(
            data,
            [
                "path_consistency_percent",
            ],
        )
    )

    profitable_percent = safe_float(
        first_value(
            data,
            [
                "profitable_percent",
            ],
        )
    )

    acceptable_percent = safe_float(
        first_value(
            data,
            [
                "acceptable_percent",
            ],
        )
    )

    worst_return = safe_float(
        first_value(
            data,
            [
                "worst_net_return_percent",
            ],
        )
    )

    worst_sharpe = safe_float(
        first_value(
            data,
            [
                "worst_sharpe_ratio",
            ],
        )
    )

    maximum_return_reduction = safe_float(
        first_value(
            data,
            [
                "maximum_return_reduction_percent",
            ],
        )
    )

    failed_scenarios = safe_int(
        first_value(
            data,
            [
                "failed_scenarios",
            ],
        )
    )

    overfitting_warning = safe_bool(
        first_value(
            data,
            [
                "overfitting_warning",
            ],
            False,
        )
    )

    if consistency_score <= 0:
        consistency_score = (
            path_consistency * 0.30
            + profitable_percent * 0.25
            + acceptable_percent * 0.20
        )

        if worst_return > 0:
            consistency_score += 15.0

        if maximum_return_reduction <= 15.0:
            consistency_score += 10.0

        elif maximum_return_reduction <= 30.0:
            consistency_score += 5.0

    reasons: list[str] = []
    warnings: list[str] = []

    if path_consistency == 100.0:
        reasons.append(
            "모든 비용 조건에서 동일한 거래 경로가 유지됐습니다."
        )

    else:
        warnings.append(
            "일부 비용 조건의 거래 경로가 기준 경로와 다릅니다."
        )

    if profitable_percent == 100.0:
        reasons.append(
            "모든 고정 거래 경로 비용 조건에서 플러스 수익을 냈습니다."
        )

    if maximum_return_reduction > 30.0:
        warnings.append(
            "고비용 조건에서 수익 감소 폭이 30%p를 초과했습니다."
        )

    raw_score = clamp_score(
        consistency_score
    )

    weight = VALIDATION_WEIGHTS[
        "execution_consistency"
    ]

    return ValidationComponent(
        component_key="execution_consistency",
        component_name="Execution Consistency",
        version="V7.9",

        weight=weight,
        raw_score=raw_score,

        weighted_score=round(
            raw_score
            * weight
            / 100.0,
            2,
        ),

        status=status,

        passed=(
            failed_scenarios == 0
            and path_consistency == 100.0
            and worst_return > 0
        ),

        warning=(
            overfitting_warning
            or maximum_return_reduction > 30.0
        ),

        source_file=str(
            source_file
        ),

        metrics={
            "consistency_score": consistency_score,
            "path_consistency_percent": path_consistency,
            "profitable_percent": profitable_percent,
            "acceptable_percent": acceptable_percent,
            "worst_net_return_percent": worst_return,
            "worst_sharpe_ratio": worst_sharpe,
            "maximum_return_reduction_percent": maximum_return_reduction,
            "failed_scenarios": failed_scenarios,
        },

        reasons=reasons,
        warnings=warnings,
    )


def create_missing_component(
    component_key: str,
    component_name: str,
    version: str,
    source_description: str,
) -> ValidationComponent:
    """
    검증 파일이 없을 때 사용하는 결과입니다.
    """

    weight = VALIDATION_WEIGHTS[
        component_key
    ]

    return ValidationComponent(
        component_key=component_key,
        component_name=component_name,
        version=version,

        weight=weight,
        raw_score=0.0,
        weighted_score=0.0,

        status="MISSING",
        passed=False,
        warning=True,

        source_file=None,

        metrics={},
        reasons=[],

        warnings=[
            f"{source_description} 결과 파일을 찾을 수 없습니다."
        ],

        error_type="FileNotFoundError",
        error_message=(
            f"{source_description} latest JSON 파일이 없습니다."
        ),
    )


def create_failed_component(
    component_key: str,
    component_name: str,
    version: str,
    source_file: Path | None,
    error: Exception,
) -> ValidationComponent:
    """
    검증 파일을 읽거나 평가하다 실패한 경우입니다.
    """

    weight = VALIDATION_WEIGHTS[
        component_key
    ]

    return ValidationComponent(
        component_key=component_key,
        component_name=component_name,
        version=version,

        weight=weight,
        raw_score=0.0,
        weighted_score=0.0,

        status="FAILED",
        passed=False,
        warning=True,

        source_file=(
            str(source_file)
            if source_file is not None
            else None
        ),

        metrics={},
        reasons=[],

        warnings=[
            "검증 결과를 읽거나 평가하는 중 오류가 발생했습니다."
        ],

        error_type=type(
            error
        ).__name__,

        error_message=str(
            error
        ),
    )


def determine_final_status(
    final_score: float,
    critical_failure: bool,
    missing_components: int,
) -> tuple[
    str,
    str,
]:
    """
    종합 검증 상태와 배포 준비 상태를 판정합니다.
    """

    if critical_failure:
        return (
            "FAILED",
            "NOT_READY",
        )

    if missing_components >= 3:
        return (
            "INCOMPLETE",
            "NOT_READY",
        )

    if final_score >= 85.0:
        return (
            "ROBUST",
            "PAPER_TRADING_READY",
        )

    if final_score >= 70.0:
        return (
            "ACCEPTABLE",
            "LIMITED_PAPER_TRADING",
        )

    if final_score >= 55.0:
        return (
            "WEAK",
            "RESEARCH_ONLY",
        )

    return (
        "FAILED",
        "NOT_READY",
    )


def evaluate_overall_result(
    components: list[
        ValidationComponent
    ],
    final_score: float,
) -> tuple[
    bool,
    list[str],
    list[str],
    list[str],
]:
    """
    전체 강점, 약점 및 다음 권장 작업을 생성합니다.
    """

    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []

    component_map = {
        component.component_key: component
        for component in components
    }

    for component in components:
        if component.passed:
            strengths.append(
                f"{component.component_name} 검증을 통과했습니다."
            )

        if component.status in {
            "MISSING",
            "FAILED",
        }:
            weaknesses.append(
                f"{component.component_name} 결과가 없거나 실패했습니다."
            )

        elif component.raw_score < 60.0:
            weaknesses.append(
                f"{component.component_name} 점수가 "
                f"{component.raw_score:.2f}/100으로 낮습니다."
            )

        for warning in component.warnings:
            weaknesses.append(
                f"{component.component_name}: {warning}"
            )

    execution_component = component_map.get(
        "execution_consistency"
    )

    if execution_component is not None:
        reduction = safe_float(
            execution_component.metrics.get(
                "maximum_return_reduction_percent"
            )
        )

        if reduction > 30.0:
            recommendations.append(
                "거래 횟수를 줄이거나 평균 보유기간을 늘려 "
                "거래비용 민감도를 낮추세요."
            )

    walk_forward_component = component_map.get(
        "walk_forward"
    )

    if walk_forward_component is not None:
        if walk_forward_component.warning:
            recommendations.append(
                "Walk-Forward 검증 구간을 추가하고 "
                "최근 데이터에서도 반복 검증하세요."
            )

    multi_period_component = component_map.get(
        "multi_period_robustness"
    )

    if multi_period_component is not None:
        if multi_period_component.warning:
            recommendations.append(
                "상승장, 하락장 및 횡보장 구간을 분리해 "
                "시장 상태별 성과를 검사하세요."
            )

    if final_score >= 70.0:
        recommendations.append(
            "실거래 전 최소 3개월 이상 Paper Trading으로 "
            "신호, 체결가격 및 거래비용을 기록하세요."
        )

    if not recommendations:
        recommendations.append(
            "누락된 검증을 보완하고 종합 점수를 다시 계산하세요."
        )

    overfitting_warning = any(
        component.warning
        for component in components
    )

    return (
        overfitting_warning,
        strengths,
        weaknesses,
        recommendations,
    )


def run_strategy_validation_scorecard(
    symbol: str = "AAPL",
) -> StrategyValidationScorecard:
    """
    기존 V7.3~V7.9 결과를 읽어 V8.0 종합 점수를 계산합니다.
    """

    normalized_symbol = (
        symbol
        .strip()
        .upper()
    )

    if not normalized_symbol:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    started_at = datetime.now()

    print()
    print("=" * 120)
    print(
        f"{normalized_symbol} V8.0 "
        "STRATEGY VALIDATION SCORECARD"
    )
    print("=" * 120)

    component_specs = [
        {
            "key": "out_of_sample",
            "name": "Out-of-Sample Validation",
            "version": "V7.3",
            "directory": "out_of_sample",
            "filenames": [
                (
                    f"{normalized_symbol}_"
                    "out_of_sample_latest.json"
                ),
            ],
            "calculator": calculate_out_of_sample_component,
        },

        {
            "key": "walk_forward",
            "name": "Walk-Forward Validation",
            "version": "V7.4",
            "directory": "walk_forward",
            "filenames": [
                (
                    f"{normalized_symbol}_"
                    "walk_forward_latest.json"
                ),
            ],
            "calculator": calculate_walk_forward_component,
        },

        {
            "key": "parameter_robustness",
            "name": "Parameter Robustness",
            "version": "V7.5",
            "directory": "parameter_robustness",
            "filenames": [
                (
                    f"{normalized_symbol}_"
                    "parameter_robustness_latest.json"
                ),
            ],
            "calculator": calculate_parameter_robustness_component,
        },

        {
            "key": "multi_period_robustness",
            "name": "Multi-Period Robustness",
            "version": "V7.6",
            "directory": "multi_period_robustness",
            "filenames": [
                (
                    f"{normalized_symbol}_"
                    "multi_period_latest.json"
                ),
                (
                    f"{normalized_symbol}_"
                    "multi_period_robustness_latest.json"
                ),
            ],
            "calculator": calculate_multi_period_component,
        },

        {
            "key": "trading_cost_stress",
            "name": "Trading Cost Stress",
            "version": "V7.7",
            "directory": "trading_cost_stress",
            "filenames": [
                (
                    f"{normalized_symbol}_"
                    "trading_cost_stress_latest.json"
                ),
            ],
            "calculator": calculate_trading_cost_component,
        },

        {
            "key": "realistic_execution",
            "name": "Realistic Execution",
            "version": "V7.8",
            "directory": "realistic_execution",
            "filenames": [
                (
                    f"{normalized_symbol}_"
                    "realistic_execution_latest.json"
                ),
            ],
            "calculator": calculate_realistic_execution_component,
        },

        {
            "key": "execution_consistency",
            "name": "Execution Consistency",
            "version": "V7.9",
            "directory": "execution_consistency",
            "filenames": [
                (
                    f"{normalized_symbol}_"
                    "execution_consistency_latest.json"
                ),
            ],
            "calculator": calculate_execution_consistency_component,
        },
    ]

    components: list[
        ValidationComponent
    ] = []

    for number, spec in enumerate(
        component_specs,
        start=1,
    ):
        print(
            f"[{number}/{len(component_specs)}] "
            f"Loading {spec['version']} "
            f"{spec['name']}..."
        )

        source_file = find_latest_file(
            directory_name=str(
                spec["directory"]
            ),

            symbol=normalized_symbol,

            preferred_names=list(
                spec["filenames"]
            ),
        )

        if source_file is None:
            component = create_missing_component(
                component_key=str(
                    spec["key"]
                ),

                component_name=str(
                    spec["name"]
                ),

                version=str(
                    spec["version"]
                ),

                source_description=str(
                    spec["name"]
                ),
            )

            components.append(
                component
            )

            print(
                "    MISSING"
            )

            continue

        try:
            payload = load_json_file(
                source_file
            )

            calculator = spec[
                "calculator"
            ]

            component = calculator(
                payload,
                source_file,
            )

            components.append(
                component
            )

            print(
                f"    Score {component.raw_score:.2f}/100 | "
                f"Weighted {component.weighted_score:.2f} | "
                f"{component.status}"
            )

        except Exception as error:
            component = create_failed_component(
                component_key=str(
                    spec["key"]
                ),

                component_name=str(
                    spec["name"]
                ),

                version=str(
                    spec["version"]
                ),

                source_file=source_file,
                error=error,
            )

            components.append(
                component
            )

            print(
                f"    FAILED: "
                f"{type(error).__name__} - {error}"
            )

    total_weight = sum(
        component.weight
        for component in components
    )

    earned_weighted_score = sum(
        component.weighted_score
        for component in components
    )

    final_score = (
        earned_weighted_score
        / total_weight
        * 100.0
        if total_weight > 0
        else 0.0
    )

    final_score = clamp_score(
        final_score
    )

    loaded_components = sum(
        1
        for component in components
        if component.status
        not in {
            "MISSING",
            "FAILED",
        }
    )

    missing_components = sum(
        1
        for component in components
        if component.status == "MISSING"
    )

    failed_components = sum(
        1
        for component in components
        if component.status == "FAILED"
    )

    passed_components = sum(
        1
        for component in components
        if component.passed
    )

    warning_components = sum(
        1
        for component in components
        if component.warning
    )

    critical_keys = {
        "out_of_sample",
        "walk_forward",
        "execution_consistency",
    }

    critical_failure = any(
        (
            component.component_key
            in critical_keys
        )
        and (
            component.status
            in {
                "MISSING",
                "FAILED",
            }
            or component.raw_score < 40.0
        )
        for component in components
    )

    (
        validation_status,
        deployment_readiness,
    ) = determine_final_status(
        final_score=final_score,
        critical_failure=critical_failure,
        missing_components=missing_components,
    )

    (
        overfitting_warning,
        strengths,
        weaknesses,
        recommendations,
    ) = evaluate_overall_result(
        components=components,
        final_score=final_score,
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return StrategyValidationScorecard(
        version="V8.0",
        symbol=normalized_symbol,

        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),

        elapsed_seconds=round(
            elapsed_seconds,
            2,
        ),

        total_components=len(
            components
        ),

        loaded_components=loaded_components,
        missing_components=missing_components,
        failed_components=failed_components,

        total_weight=round(
            total_weight,
            2,
        ),

        earned_weighted_score=round(
            earned_weighted_score,
            2,
        ),

        final_score=final_score,

        passed_components=passed_components,
        warning_components=warning_components,

        validation_status=validation_status,
        deployment_readiness=deployment_readiness,

        critical_failure=critical_failure,
        overfitting_warning=overfitting_warning,

        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,

        components=[
            component.to_dict()
            for component in components
        ],
    )


def save_strategy_validation_scorecard(
    result: StrategyValidationScorecard,
) -> tuple[
    Path,
    Path,
]:
    """
    V8.0 점수표를 JSON 파일로 저장합니다.
    """

    SCORECARD_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        SCORECARD_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_validation_scorecard_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        SCORECARD_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_validation_scorecard_"
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


def print_strategy_validation_scorecard(
    result: StrategyValidationScorecard,
) -> None:
    """
    V8.0 종합 점수표를 터미널에 출력합니다.
    """

    print()
    print("=" * 130)
    print(
        f"{result.symbol} V8.0 "
        "STRATEGY VALIDATION SCORECARD RESULT"
    )
    print("=" * 130)

    print(
        f"Final score                  : "
        f"{result.final_score:.2f}/100"
    )

    print(
        f"Validation status            : "
        f"{result.validation_status}"
    )

    print(
        f"Deployment readiness         : "
        f"{result.deployment_readiness}"
    )

    print(
        f"Critical failure             : "
        f"{result.critical_failure}"
    )

    print(
        f"Overfitting warning          : "
        f"{result.overfitting_warning}"
    )

    print()
    print("COMPONENT SUMMARY")
    print("-" * 130)

    print(
        f"Total components             : "
        f"{result.total_components}"
    )

    print(
        f"Loaded components            : "
        f"{result.loaded_components}"
    )

    print(
        f"Missing components           : "
        f"{result.missing_components}"
    )

    print(
        f"Failed components            : "
        f"{result.failed_components}"
    )

    print(
        f"Passed components            : "
        f"{result.passed_components}"
    )

    print(
        f"Warning components           : "
        f"{result.warning_components}"
    )

    print()
    print("VALIDATION COMPONENTS")
    print("-" * 130)

    print(
        f"{'No.':<5}"
        f"{'Version':<10}"
        f"{'Validation':<32}"
        f"{'Weight':>10}"
        f"{'Score':>12}"
        f"{'Weighted':>12}"
        f"{'Passed':>10}"
        f"{'Warning':>10}"
        f"{'Status':>16}"
    )

    print("-" * 130)

    for number, component in enumerate(
        result.components,
        start=1,
    ):
        print(
            f"{number:<5}"
            f"{component['version']:<10}"
            f"{component['component_name']:<32}"
            f"{float(component['weight']):>9.2f}%"
            f"{float(component['raw_score']):>11.2f}"
            f"{float(component['weighted_score']):>12.2f}"
            f"{str(component['passed']):>10}"
            f"{str(component['warning']):>10}"
            f"{str(component['status']):>16}"
        )

    if result.strengths:
        print()
        print("STRENGTHS")
        print("-" * 130)

        for strength in result.strengths:
            print(
                f"- {strength}"
            )

    if result.weaknesses:
        print()
        print("WEAKNESSES")
        print("-" * 130)

        for weakness in result.weaknesses:
            print(
                f"- {weakness}"
            )

    if result.recommendations:
        print()
        print("NEXT RECOMMENDATIONS")
        print("-" * 130)

        for recommendation in result.recommendations:
            print(
                f"- {recommendation}"
            )

    print()
    print("FILES")
    print("-" * 130)

    print(
        f"Report file                  : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                  : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 130)

    print(
        "주의: 이 점수표는 과거 데이터 기반 검증 결과를 종합한 "
        "연구용 평가이며 실제 투자 조언이나 수익 보장이 아닙니다."
    )