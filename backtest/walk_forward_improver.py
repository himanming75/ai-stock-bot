import json
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DIAGNOSTIC_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "walk_forward_diagnostic"
)

IMPROVEMENT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "walk_forward_improvement"
)


@dataclass
class ImprovementCandidate:
    """
    Walk-Forward 개선 후보 파라미터입니다.
    """

    candidate_number: int
    candidate_name: str
    candidate_type: str

    entry_score: float
    exit_score: float
    stop_atr_multiple: float
    target_atr_multiple: float
    maximum_holding_days: int
    position_percent: float

    entry_change: float
    exit_change: float
    stop_atr_change: float
    target_atr_change: float
    holding_days_change: int
    position_percent_change: float

    estimated_selectivity: str
    estimated_trade_frequency: str
    estimated_risk_level: str

    priority_score: float
    recommendation_status: str

    reasons: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WalkForwardImprovementResult:
    """
    V8.2 Walk-Forward 개선 후보 생성 결과입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    source_file: str

    diagnostic_status: str
    diagnostic_score: float
    recent_trend: str
    overfitting_warning: bool

    base_entry_score: float
    base_exit_score: float
    base_stop_atr: float
    base_target_atr: float
    base_holding_days: int
    base_position_percent: float

    total_candidates: int
    conservative_candidates: int
    balanced_candidates: int
    aggressive_candidates: int

    high_priority_candidates: int
    medium_priority_candidates: int
    low_priority_candidates: int

    recommended_candidate_number: int | None
    recommended_candidate_name: str | None
    recommended_priority_score: float

    critical_problems: list[str]
    diagnostic_recommendations: list[str]

    candidates: list[dict[str, Any]]

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


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 정규화합니다.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def find_latest_diagnostic_file(
    symbol: str,
) -> Path:
    """
    V8.1 Walk-Forward Diagnostic latest 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    expected_path = (
        DIAGNOSTIC_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "walk_forward_diagnostic_latest.json"
        )
    )

    if expected_path.exists():
        return expected_path

    if not DIAGNOSTIC_DIRECTORY.exists():
        raise FileNotFoundError(
            "Walk-Forward Diagnostic 폴더가 없습니다: "
            f"{DIAGNOSTIC_DIRECTORY}"
        )

    candidates = list(
        DIAGNOSTIC_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "walk_forward_diagnostic_*.json"
        )
    )

    candidates = [
        path
        for path in candidates
        if "latest" not in path.name.lower()
    ]

    if not candidates:
        raise FileNotFoundError(
            f"{normalized_symbol} V8.1 Diagnostic "
            "결과 파일을 찾을 수 없습니다."
        )

    return max(
        candidates,
        key=lambda path: path.stat().st_mtime,
    )


def load_diagnostic_result(
    source_path: Path,
) -> dict[str, Any]:
    """
    V8.1 Diagnostic JSON 파일을 읽습니다.
    """

    if not source_path.exists():
        raise FileNotFoundError(
            f"진단 파일이 없습니다: {source_path}"
        )

    with source_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            "Diagnostic JSON의 최상위 데이터가 "
            "객체 형식이 아닙니다."
        )

    return payload


def normalize_entry_score(
    value: float,
) -> float:
    """
    진입 점수를 유효 범위로 제한합니다.
    """

    return round(
        max(
            50.0,
            min(
                90.0,
                value,
            ),
        ),
        2,
    )


def normalize_exit_score(
    value: float,
) -> float:
    """
    청산 점수를 유효 범위로 제한합니다.
    """

    return round(
        max(
            20.0,
            min(
                70.0,
                value,
            ),
        ),
        2,
    )


def normalize_stop_atr(
    value: float,
) -> float:
    """
    Stop ATR을 유효 범위로 제한합니다.
    """

    return round(
        max(
            0.75,
            min(
                3.0,
                value,
            ),
        ),
        2,
    )


def normalize_target_atr(
    value: float,
) -> float:
    """
    Target ATR을 유효 범위로 제한합니다.
    """

    return round(
        max(
            1.0,
            min(
                5.0,
                value,
            ),
        ),
        2,
    )


def normalize_holding_days(
    value: int,
) -> int:
    """
    최대 보유기간을 유효 범위로 제한합니다.
    """

    return max(
        5,
        min(
            60,
            int(value),
        ),
    )


def normalize_position_percent(
    value: float,
) -> float:
    """
    포지션 비율을 유효 범위로 제한합니다.
    """

    return round(
        max(
            5.0,
            min(
                30.0,
                value,
            ),
        ),
        2,
    )


def classify_candidate_type(
    entry_change: float,
    stop_change: float,
    position_change: float,
) -> str:
    """
    후보의 성격을 분류합니다.
    """

    if (
        entry_change >= 2.0
        or stop_change <= -0.25
        or position_change < 0
    ):
        return "CONSERVATIVE"

    if (
        entry_change <= -2.0
        or stop_change >= 0.25
        or position_change > 0
    ):
        return "AGGRESSIVE"

    return "BALANCED"


def estimate_selectivity(
    entry_change: float,
) -> str:
    """
    진입 선택성 변화를 추정합니다.
    """

    if entry_change >= 4.0:
        return "VERY_HIGH"

    if entry_change >= 2.0:
        return "HIGH"

    if entry_change <= -4.0:
        return "LOW"

    if entry_change <= -2.0:
        return "MEDIUM_LOW"

    return "MEDIUM"


def estimate_trade_frequency(
    entry_change: float,
    holding_change: int,
) -> str:
    """
    예상 거래 빈도를 추정합니다.
    """

    frequency_score = 0

    if entry_change >= 4:
        frequency_score -= 2

    elif entry_change >= 2:
        frequency_score -= 1

    elif entry_change <= -4:
        frequency_score += 2

    elif entry_change <= -2:
        frequency_score += 1

    if holding_change >= 10:
        frequency_score -= 1

    elif holding_change <= -10:
        frequency_score += 1

    if frequency_score >= 2:
        return "HIGH"

    if frequency_score == 1:
        return "MEDIUM_HIGH"

    if frequency_score <= -2:
        return "LOW"

    if frequency_score == -1:
        return "MEDIUM_LOW"

    return "MEDIUM"


def estimate_risk_level(
    stop_atr: float,
    position_percent: float,
    target_atr: float,
) -> str:
    """
    후보 전략의 위험 수준을 추정합니다.
    """

    risk_score = 0

    if stop_atr >= 2.0:
        risk_score += 2

    elif stop_atr >= 1.75:
        risk_score += 1

    if position_percent >= 25.0:
        risk_score += 2

    elif position_percent >= 20.0:
        risk_score += 1

    if target_atr >= 3.5:
        risk_score += 1

    if risk_score >= 4:
        return "HIGH"

    if risk_score >= 2:
        return "MEDIUM"

    return "LOW"


def calculate_priority_score(
    candidate_type: str,
    entry_change: float,
    exit_change: float,
    stop_change: float,
    target_change: float,
    holding_change: int,
    position_change: float,
    recent_trend: str,
    overfitting_warning: bool,
    diagnostic_score: float,
) -> float:
    """
    후보의 테스트 우선순위를 계산합니다.
    """

    score = 50.0

    if candidate_type == "CONSERVATIVE":
        score += 12.0

    elif candidate_type == "BALANCED":
        score += 8.0

    else:
        score -= 4.0

    if overfitting_warning:
        if candidate_type == "CONSERVATIVE":
            score += 12.0

        if position_change < 0:
            score += 8.0

        if entry_change > 0:
            score += 8.0

    if recent_trend == "DETERIORATING":
        if entry_change > 0:
            score += 10.0

        if position_change < 0:
            score += 8.0

        if stop_change < 0:
            score += 5.0

    elif recent_trend == "IMPROVING":
        if candidate_type == "BALANCED":
            score += 5.0

    if diagnostic_score < 40.0:
        if candidate_type == "CONSERVATIVE":
            score += 10.0

        if candidate_type == "AGGRESSIVE":
            score -= 12.0

    elif diagnostic_score < 60.0:
        if candidate_type == "BALANCED":
            score += 5.0

    change_size = (
        abs(entry_change) / 2.0
        + abs(exit_change) / 2.0
        + abs(stop_change) * 4.0
        + abs(target_change) * 3.0
        + abs(holding_change) / 5.0
        + abs(position_change) / 2.5
    )

    if change_size <= 5.0:
        score += 8.0

    elif change_size >= 14.0:
        score -= 10.0

    return clamp_score(score)


def determine_recommendation_status(
    priority_score: float,
    risk_level: str,
) -> str:
    """
    후보 추천 등급을 결정합니다.
    """

    if (
        priority_score >= 75.0
        and risk_level != "HIGH"
    ):
        return "HIGH_PRIORITY"

    if priority_score >= 55.0:
        return "MEDIUM_PRIORITY"

    return "LOW_PRIORITY"


def build_candidate_notes(
    candidate_type: str,
    entry_change: float,
    exit_change: float,
    stop_change: float,
    target_change: float,
    holding_change: int,
    position_change: float,
    diagnostic_problems: list[str],
    recent_trend: str,
    overfitting_warning: bool,
) -> tuple[list[str], list[str]]:
    """
    후보 변경 이유와 경고를 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if entry_change > 0:
        reasons.append(
            "진입 점수를 높여 약한 매수 신호를 줄입니다."
        )

    elif entry_change < 0:
        reasons.append(
            "진입 점수를 낮춰 거래 기회를 늘립니다."
        )

    if exit_change > 0:
        reasons.append(
            "청산 점수를 높여 약한 상태에서 더 빠르게 "
            "포지션을 종료하도록 조정합니다."
        )

    elif exit_change < 0:
        reasons.append(
            "청산 점수를 낮춰 추세를 더 오래 보유하도록 "
            "조정합니다."
        )

    if stop_change < 0:
        reasons.append(
            "손절 폭을 줄여 개별 거래 손실을 제한합니다."
        )

    elif stop_change > 0:
        reasons.append(
            "손절 폭을 넓혀 단기 가격 변동에 의한 "
            "조기 청산을 줄입니다."
        )

    if target_change > 0:
        reasons.append(
            "목표 수익 폭을 높여 이익 거래의 기대수익을 "
            "확대합니다."
        )

    elif target_change < 0:
        reasons.append(
            "목표 수익 폭을 낮춰 이익 실현 가능성을 높입니다."
        )

    if holding_change > 0:
        reasons.append(
            "최대 보유기간을 늘려 중기 추세를 더 오래 "
            "추적합니다."
        )

    elif holding_change < 0:
        reasons.append(
            "최대 보유기간을 줄여 자금 회전과 위험 관리를 "
            "강화합니다."
        )

    if position_change < 0:
        reasons.append(
            "포지션 비율을 줄여 전략 불확실성에 대한 "
            "노출을 낮춥니다."
        )

    elif position_change > 0:
        reasons.append(
            "포지션 비율을 높여 강한 신호에서의 "
            "수익 기회를 확대합니다."
        )

    if diagnostic_problems:
        reasons.append(
            "V8.1 진단에서 발견된 문제를 반영한 "
            "개선 후보입니다."
        )

    if recent_trend == "DETERIORATING":
        reasons.append(
            "최근 Walk-Forward 성과 악화를 반영했습니다."
        )

    if overfitting_warning:
        warnings.append(
            "기존 전략에 과최적화 경고가 있으므로 "
            "반드시 별도의 Walk-Forward 검증이 필요합니다."
        )

    if candidate_type == "AGGRESSIVE":
        warnings.append(
            "공격형 후보는 거래 횟수와 손실 변동성이 "
            "증가할 수 있습니다."
        )

    if position_change > 0:
        warnings.append(
            "포지션 비율 증가로 최대 낙폭과 손실 금액이 "
            "커질 수 있습니다."
        )

    if stop_change > 0:
        warnings.append(
            "넓은 손절 폭은 한 거래의 손실 크기를 "
            "증가시킬 수 있습니다."
        )

    if not reasons:
        reasons.append(
            "현재 공통 파라미터를 기준 후보로 유지합니다."
        )

    return (
        reasons,
        warnings,
    )


def generate_candidate_combinations(
    base_entry: float,
    base_exit: float,
    base_stop: float,
    base_target: float,
    base_holding: int,
    base_position: float,
    maximum_candidates: int,
) -> list[tuple[float, float, float, float, int, float]]:
    """
    공통 파라미터 주변의 후보 조합을 생성합니다.
    """

    entry_values = sorted(
        {
            normalize_entry_score(
                base_entry + change
            )
            for change in (
                -2.0,
                0.0,
                2.0,
                4.0,
            )
        }
    )

    exit_values = sorted(
        {
            normalize_exit_score(
                base_exit + change
            )
            for change in (
                -2.0,
                0.0,
                2.0,
            )
        }
    )

    stop_values = sorted(
        {
            normalize_stop_atr(
                base_stop + change
            )
            for change in (
                -0.25,
                0.0,
                0.25,
            )
        }
    )

    target_values = sorted(
        {
            normalize_target_atr(
                base_target + change
            )
            for change in (
                -0.25,
                0.0,
                0.25,
                0.50,
            )
        }
    )

    holding_values = sorted(
        {
            normalize_holding_days(
                base_holding + change
            )
            for change in (
                -10,
                0,
                10,
            )
        }
    )

    position_values = sorted(
        {
            normalize_position_percent(
                base_position + change
            )
            for change in (
                -5.0,
                0.0,
            )
        }
    )

    all_combinations = list(
        product(
            entry_values,
            exit_values,
            stop_values,
            target_values,
            holding_values,
            position_values,
        )
    )

    base_combination = (
        normalize_entry_score(base_entry),
        normalize_exit_score(base_exit),
        normalize_stop_atr(base_stop),
        normalize_target_atr(base_target),
        normalize_holding_days(base_holding),
        normalize_position_percent(base_position),
    )

    unique_combinations = list(
        dict.fromkeys(
            all_combinations
        )
    )

    unique_combinations.sort(
        key=lambda combination: (
            0
            if combination == base_combination
            else 1,

            abs(
                combination[0]
                - base_entry
            ),

            abs(
                combination[1]
                - base_exit
            ),

            abs(
                combination[2]
                - base_stop
            ),

            abs(
                combination[3]
                - base_target
            ),

            abs(
                combination[4]
                - base_holding
            ),

            abs(
                combination[5]
                - base_position
            ),
        )
    )

    return unique_combinations[
        :maximum_candidates
    ]


def run_walk_forward_improvement_generator(
    symbol: str = "AAPL",
    source_file: str | Path | None = None,
    maximum_candidates: int = 30,
) -> WalkForwardImprovementResult:
    """
    V8.1 진단을 바탕으로 V8.2 개선 후보를 생성합니다.
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
    print("=" * 140)
    print(
        f"{normalized_symbol} V8.2 "
        "WALK-FORWARD IMPROVEMENT GENERATOR"
    )
    print("=" * 140)

    if source_file is None:
        source_path = (
            find_latest_diagnostic_file(
                normalized_symbol
            )
        )

    else:
        source_path = Path(
            source_file
        )

    print(
        f"Source diagnostic       : "
        f"{source_path}"
    )

    diagnostic = load_diagnostic_result(
        source_path
    )

    diagnostic_status = str(
        diagnostic.get(
            "validation_status",
            "UNKNOWN",
        )
    ).upper()

    diagnostic_score = safe_float(
        diagnostic.get(
            "overall_diagnostic_score",
            0.0,
        )
    )

    recent_trend = str(
        diagnostic.get(
            "recent_trend",
            "UNKNOWN",
        )
    ).upper()

    overfitting_warning = safe_bool(
        diagnostic.get(
            "overfitting_warning",
            False,
        )
    )

    base_entry = safe_float(
        diagnostic.get(
            "most_common_entry_score",
            64.0,
        ),
        64.0,
    )

    base_exit = safe_float(
        diagnostic.get(
            "most_common_exit_score",
            42.0,
        ),
        42.0,
    )

    base_stop = safe_float(
        diagnostic.get(
            "most_common_stop_atr",
            1.50,
        ),
        1.50,
    )

    base_target = safe_float(
        diagnostic.get(
            "most_common_target_atr",
            2.50,
        ),
        2.50,
    )

    base_holding = safe_int(
        diagnostic.get(
            "most_common_holding_days",
            20,
        ),
        20,
    )

    base_position = 20.0

    raw_windows = diagnostic.get(
        "windows",
        [],
    )

    if isinstance(raw_windows, list):
        valid_positions = [
            safe_float(
                window.get(
                    "position_percent",
                    20.0,
                ),
                20.0,
            )
            for window in raw_windows
            if isinstance(window, dict)
        ]

        if valid_positions:
            base_position = round(
                sum(valid_positions)
                / len(valid_positions),
                2,
            )

    critical_problems = diagnostic.get(
        "critical_problems",
        [],
    )

    if not isinstance(
        critical_problems,
        list,
    ):
        critical_problems = []

    diagnostic_recommendations = diagnostic.get(
        "recommendations",
        [],
    )

    if not isinstance(
        diagnostic_recommendations,
        list,
    ):
        diagnostic_recommendations = []

    print(
        f"Diagnostic status       : "
        f"{diagnostic_status}"
    )

    print(
        f"Diagnostic score        : "
        f"{diagnostic_score:.2f}/100"
    )

    print(
        f"Recent trend            : "
        f"{recent_trend}"
    )

    print(
        f"Overfitting warning     : "
        f"{overfitting_warning}"
    )

    print()
    print("BASE PARAMETERS")
    print("-" * 140)

    print(
        f"Entry score             : "
        f"{base_entry:.2f}"
    )

    print(
        f"Exit score              : "
        f"{base_exit:.2f}"
    )

    print(
        f"Stop ATR                : "
        f"{base_stop:.2f}"
    )

    print(
        f"Target ATR              : "
        f"{base_target:.2f}"
    )

    print(
        f"Holding days            : "
        f"{base_holding}"
    )

    print(
        f"Position percent        : "
        f"{base_position:.2f}%"
    )

    combinations = generate_candidate_combinations(
        base_entry=base_entry,
        base_exit=base_exit,
        base_stop=base_stop,
        base_target=base_target,
        base_holding=base_holding,
        base_position=base_position,
        maximum_candidates=maximum_candidates,
    )

    candidates: list[
        ImprovementCandidate
    ] = []

    for candidate_number, combination in enumerate(
        combinations,
        start=1,
    ):
        (
            entry_score,
            exit_score,
            stop_atr,
            target_atr,
            holding_days,
            position_percent,
        ) = combination

        entry_change = round(
            entry_score - base_entry,
            2,
        )

        exit_change = round(
            exit_score - base_exit,
            2,
        )

        stop_change = round(
            stop_atr - base_stop,
            2,
        )

        target_change = round(
            target_atr - base_target,
            2,
        )

        holding_change = (
            holding_days
            - base_holding
        )

        position_change = round(
            position_percent
            - base_position,
            2,
        )

        candidate_type = classify_candidate_type(
            entry_change=entry_change,
            stop_change=stop_change,
            position_change=position_change,
        )

        selectivity = estimate_selectivity(
            entry_change=entry_change
        )

        trade_frequency = (
            estimate_trade_frequency(
                entry_change=entry_change,
                holding_change=holding_change,
            )
        )

        risk_level = estimate_risk_level(
            stop_atr=stop_atr,
            position_percent=position_percent,
            target_atr=target_atr,
        )

        priority_score = (
            calculate_priority_score(
                candidate_type=candidate_type,
                entry_change=entry_change,
                exit_change=exit_change,
                stop_change=stop_change,
                target_change=target_change,
                holding_change=holding_change,
                position_change=position_change,
                recent_trend=recent_trend,
                overfitting_warning=(
                    overfitting_warning
                ),
                diagnostic_score=(
                    diagnostic_score
                ),
            )
        )

        recommendation_status = (
            determine_recommendation_status(
                priority_score=priority_score,
                risk_level=risk_level,
            )
        )

        (
            reasons,
            warnings,
        ) = build_candidate_notes(
            candidate_type=candidate_type,
            entry_change=entry_change,
            exit_change=exit_change,
            stop_change=stop_change,
            target_change=target_change,
            holding_change=holding_change,
            position_change=position_change,
            diagnostic_problems=[
                str(problem)
                for problem in critical_problems
            ],
            recent_trend=recent_trend,
            overfitting_warning=(
                overfitting_warning
            ),
        )

        if candidate_number == 1:
            candidate_name = (
                "BASELINE_REFERENCE"
            )

        else:
            candidate_name = (
                f"{candidate_type}_"
                f"CANDIDATE_{candidate_number:02d}"
            )

        candidate = ImprovementCandidate(
            candidate_number=(
                candidate_number
            ),

            candidate_name=(
                candidate_name
            ),

            candidate_type=(
                candidate_type
            ),

            entry_score=entry_score,
            exit_score=exit_score,

            stop_atr_multiple=(
                stop_atr
            ),

            target_atr_multiple=(
                target_atr
            ),

            maximum_holding_days=(
                holding_days
            ),

            position_percent=(
                position_percent
            ),

            entry_change=entry_change,
            exit_change=exit_change,

            stop_atr_change=(
                stop_change
            ),

            target_atr_change=(
                target_change
            ),

            holding_days_change=(
                holding_change
            ),

            position_percent_change=(
                position_change
            ),

            estimated_selectivity=(
                selectivity
            ),

            estimated_trade_frequency=(
                trade_frequency
            ),

            estimated_risk_level=(
                risk_level
            ),

            priority_score=(
                priority_score
            ),

            recommendation_status=(
                recommendation_status
            ),

            reasons=reasons,
            warnings=warnings,
        )

        candidates.append(
            candidate
        )

    candidates.sort(
        key=lambda item: (
            item.priority_score,
            item.candidate_type
            == "CONSERVATIVE",
            -item.candidate_number,
        ),
        reverse=True,
    )

    for new_number, candidate in enumerate(
        candidates,
        start=1,
    ):
        candidate.candidate_number = (
            new_number
        )

    recommended_candidate = (
        candidates[0]
        if candidates
        else None
    )

    conservative_count = sum(
        1
        for candidate in candidates
        if candidate.candidate_type
        == "CONSERVATIVE"
    )

    balanced_count = sum(
        1
        for candidate in candidates
        if candidate.candidate_type
        == "BALANCED"
    )

    aggressive_count = sum(
        1
        for candidate in candidates
        if candidate.candidate_type
        == "AGGRESSIVE"
    )

    high_priority_count = sum(
        1
        for candidate in candidates
        if candidate.recommendation_status
        == "HIGH_PRIORITY"
    )

    medium_priority_count = sum(
        1
        for candidate in candidates
        if candidate.recommendation_status
        == "MEDIUM_PRIORITY"
    )

    low_priority_count = sum(
        1
        for candidate in candidates
        if candidate.recommendation_status
        == "LOW_PRIORITY"
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    result = WalkForwardImprovementResult(
        version="V8.2",
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

        diagnostic_status=(
            diagnostic_status
        ),

        diagnostic_score=round(
            diagnostic_score,
            2,
        ),

        recent_trend=recent_trend,

        overfitting_warning=(
            overfitting_warning
        ),

        base_entry_score=round(
            base_entry,
            2,
        ),

        base_exit_score=round(
            base_exit,
            2,
        ),

        base_stop_atr=round(
            base_stop,
            2,
        ),

        base_target_atr=round(
            base_target,
            2,
        ),

        base_holding_days=(
            base_holding
        ),

        base_position_percent=round(
            base_position,
            2,
        ),

        total_candidates=len(
            candidates
        ),

        conservative_candidates=(
            conservative_count
        ),

        balanced_candidates=(
            balanced_count
        ),

        aggressive_candidates=(
            aggressive_count
        ),

        high_priority_candidates=(
            high_priority_count
        ),

        medium_priority_candidates=(
            medium_priority_count
        ),

        low_priority_candidates=(
            low_priority_count
        ),

        recommended_candidate_number=(
            recommended_candidate.candidate_number
            if recommended_candidate
            else None
        ),

        recommended_candidate_name=(
            recommended_candidate.candidate_name
            if recommended_candidate
            else None
        ),

        recommended_priority_score=(
            recommended_candidate.priority_score
            if recommended_candidate
            else 0.0
        ),

        critical_problems=[
            str(problem)
            for problem in critical_problems
        ],

        diagnostic_recommendations=[
            str(recommendation)
            for recommendation
            in diagnostic_recommendations
        ],

        candidates=[
            candidate.to_dict()
            for candidate in candidates
        ],
    )

    print()
    print(
        f"Generated candidates     : "
        f"{result.total_candidates}"
    )

    print(
        f"Recommended candidate    : "
        f"{result.recommended_candidate_name}"
    )

    print(
        f"Recommended priority     : "
        f"{result.recommended_priority_score:.2f}/100"
    )

    print("=" * 140)

    return result


def save_walk_forward_improvement(
    result: WalkForwardImprovementResult,
) -> tuple[Path, Path]:
    """
    V8.2 개선 후보 결과를 JSON으로 저장합니다.
    """

    IMPROVEMENT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        IMPROVEMENT_DIRECTORY
        / (
            f"{result.symbol}_"
            "walk_forward_improvement_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        IMPROVEMENT_DIRECTORY
        / (
            f"{result.symbol}_"
            "walk_forward_improvement_latest.json"
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


def print_walk_forward_improvement(
    result: WalkForwardImprovementResult,
) -> None:
    """
    V8.2 개선 후보 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 150)
    print(
        f"{result.symbol} V8.2 "
        "WALK-FORWARD IMPROVEMENT RESULT"
    )
    print("=" * 150)

    print(
        f"Source diagnostic             : "
        f"{result.source_file}"
    )

    print(
        f"Diagnostic status             : "
        f"{result.diagnostic_status}"
    )

    print(
        f"Diagnostic score              : "
        f"{result.diagnostic_score:.2f}/100"
    )

    print(
        f"Recent trend                  : "
        f"{result.recent_trend}"
    )

    print(
        f"Overfitting warning           : "
        f"{result.overfitting_warning}"
    )

    print()
    print("BASE PARAMETERS")
    print("-" * 150)

    print(
        f"Entry score                   : "
        f"{result.base_entry_score:.2f}"
    )

    print(
        f"Exit score                    : "
        f"{result.base_exit_score:.2f}"
    )

    print(
        f"Stop ATR                      : "
        f"{result.base_stop_atr:.2f}"
    )

    print(
        f"Target ATR                    : "
        f"{result.base_target_atr:.2f}"
    )

    print(
        f"Maximum holding days          : "
        f"{result.base_holding_days}"
    )

    print(
        f"Position percent              : "
        f"{result.base_position_percent:.2f}%"
    )

    print()
    print("CANDIDATE SUMMARY")
    print("-" * 150)

    print(
        f"Total candidates              : "
        f"{result.total_candidates}"
    )

    print(
        f"Conservative candidates       : "
        f"{result.conservative_candidates}"
    )

    print(
        f"Balanced candidates           : "
        f"{result.balanced_candidates}"
    )

    print(
        f"Aggressive candidates         : "
        f"{result.aggressive_candidates}"
    )

    print(
        f"High-priority candidates      : "
        f"{result.high_priority_candidates}"
    )

    print(
        f"Medium-priority candidates    : "
        f"{result.medium_priority_candidates}"
    )

    print(
        f"Low-priority candidates       : "
        f"{result.low_priority_candidates}"
    )

    print()
    print("CANDIDATE RANKING")
    print("-" * 150)

    print(
        f"{'Rank':<6}"
        f"{'Name':<30}"
        f"{'Type':<15}"
        f"{'Entry':>8}"
        f"{'Exit':>8}"
        f"{'Stop':>8}"
        f"{'Target':>9}"
        f"{'Hold':>8}"
        f"{'Pos%':>8}"
        f"{'Risk':>12}"
        f"{'Priority':>11}"
        f"{'Status':>18}"
    )

    print("-" * 150)

    for candidate in result.candidates:
        print(
            f"{int(candidate['candidate_number']):<6}"
            f"{str(candidate['candidate_name']):<30}"
            f"{str(candidate['candidate_type']):<15}"
            f"{float(candidate['entry_score']):>8.2f}"
            f"{float(candidate['exit_score']):>8.2f}"
            f"{float(candidate['stop_atr_multiple']):>8.2f}"
            f"{float(candidate['target_atr_multiple']):>9.2f}"
            f"{int(candidate['maximum_holding_days']):>8}"
            f"{float(candidate['position_percent']):>8.2f}"
            f"{str(candidate['estimated_risk_level']):>12}"
            f"{float(candidate['priority_score']):>11.2f}"
            f"{str(candidate['recommendation_status']):>18}"
        )

    if result.candidates:
        recommended = result.candidates[0]

        print()
        print("TOP RECOMMENDED CANDIDATE")
        print("-" * 150)

        print(
            f"Candidate number              : "
            f"{recommended['candidate_number']}"
        )

        print(
            f"Candidate name                : "
            f"{recommended['candidate_name']}"
        )

        print(
            f"Candidate type                : "
            f"{recommended['candidate_type']}"
        )

        print(
            f"Priority score                : "
            f"{float(recommended['priority_score']):.2f}/100"
        )

        print(
            f"Recommendation status         : "
            f"{recommended['recommendation_status']}"
        )

        print(
            f"Estimated selectivity         : "
            f"{recommended['estimated_selectivity']}"
        )

        print(
            f"Estimated trade frequency     : "
            f"{recommended['estimated_trade_frequency']}"
        )

        print(
            f"Estimated risk level          : "
            f"{recommended['estimated_risk_level']}"
        )

        print()
        print("Reasons")
        print("-" * 150)

        for reason in recommended.get(
            "reasons",
            [],
        ):
            print(
                f"- {reason}"
            )

        warnings = recommended.get(
            "warnings",
            [],
        )

        if warnings:
            print()
            print("Warnings")
            print("-" * 150)

            for warning in warnings:
                print(
                    f"- {warning}"
                )

    if result.critical_problems:
        print()
        print("SOURCE DIAGNOSTIC PROBLEMS")
        print("-" * 150)

        for problem in result.critical_problems:
            print(
                f"- {problem}"
            )

    if result.diagnostic_recommendations:
        print()
        print("SOURCE DIAGNOSTIC RECOMMENDATIONS")
        print("-" * 150)

        for recommendation in (
            result.diagnostic_recommendations
        ):
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
        "주의: 생성된 후보는 아직 백테스트되지 않은 "
        "파라미터 제안입니다. 실제 적용 전에 반드시 "
        "별도의 Walk-Forward 검증이 필요합니다."
    )