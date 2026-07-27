import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

REGISTRY_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "registry"
)

CONFIGURATION_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "configurations"
)


VALID_CONFIGURATION_MODES = {
    "ACTIVE",
    "PAPER_TRADING",
    "BASELINE",
    "RESEARCH_ONLY",
    "UNAVAILABLE",
}


VALID_REGISTRY_MODES = {
    "ACTIVE",
    "PAPER_TRADING",
    "BASELINE",
    "RESEARCH_ONLY",
    "UNREGISTERED",
}


@dataclass
class StrategyConfiguration:
    """
    다른 모듈이 사용할 수 있는 표준 전략 설정입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_registry_file: str

    registry_mode: str
    configuration_mode: str
    configuration_label: str

    strategy_source: str
    strategy_status: str
    strategy_name: str | None
    strategy_type: str | None

    entry_score: float
    exit_score: float
    stop_atr_multiple: float
    target_atr_multiple: float
    maximum_holding_days: int
    position_percent: float

    candidate_score: float | None
    baseline_score: float | None
    score_improvement: float | None

    confidence_score: float | None
    confidence_level: str

    risk_score: float | None
    risk_level: str

    recommendation_strength: int | None

    registry_ready: bool
    configuration_ready: bool

    execution_enabled: bool
    paper_execution_enabled: bool
    manual_approval_required: bool

    is_default_configuration: bool
    fallback_used: bool

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_BASELINE_PARAMETERS = {
    "entry_score": 64.0,
    "exit_score": 42.0,
    "stop_atr_multiple": 1.50,
    "target_atr_multiple": 2.50,
    "maximum_holding_days": 20,
    "position_percent": 20.0,
}


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
    default: float | None = None,
) -> float | None:
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
    default: int | None = None,
) -> int | None:
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


def load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽습니다.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON 파일이 없습니다: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일을 이용해 안전하게 저장합니다.
    """

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    with temporary_path.open(
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

    temporary_path.replace(
        file_path
    )


def find_latest_registry_file(
    symbol: str,
) -> Path:
    """
    V8.6 최신 Registry 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    expected_path = (
        REGISTRY_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "active_strategy_registry_latest.json"
        )
    )

    if expected_path.exists():
        return expected_path

    if not REGISTRY_DIRECTORY.exists():
        raise FileNotFoundError(
            "V8.6 Registry 폴더가 없습니다: "
            f"{REGISTRY_DIRECTORY}"
        )

    matching_files = [
        path
        for path in REGISTRY_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "active_strategy_registry_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not matching_files:
        raise FileNotFoundError(
            f"{normalized_symbol} V8.6 Registry 파일을 "
            "찾을 수 없습니다."
        )

    return max(
        matching_files,
        key=lambda path: path.stat().st_mtime,
    )


def validate_registry_payload(
    payload: dict[str, Any],
) -> None:
    """
    V8.6 Registry 데이터의 필수 항목을 검사합니다.
    """

    required_keys = {
        "version",
        "symbol",
        "registry_mode",
        "registry_ready",
        "execution_enabled",
        "manual_approval_required",
        "selected_strategy_source",
        "selected_strategy_status",
        "selected_strategy_name",
        "selected_strategy_type",
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
        "candidate_score",
        "baseline_score",
        "score_improvement",
        "confidence_score",
        "confidence_level",
        "risk_score",
        "risk_level",
        "recommendation_strength",
    }

    missing_keys = (
        required_keys
        - set(payload.keys())
    )

    if missing_keys:
        raise ValueError(
            "V8.6 Registry 데이터에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    version = str(
        payload.get(
            "version",
            "",
        )
    ).upper()

    if version != "V8.6":
        raise ValueError(
            f"V8.6 Registry 파일이 아닙니다: {version}"
        )

    registry_mode = str(
        payload.get(
            "registry_mode",
            "",
        )
    ).upper()

    if registry_mode not in VALID_REGISTRY_MODES:
        raise ValueError(
            f"올바르지 않은 Registry Mode입니다: "
            f"{registry_mode}"
        )


def determine_configuration_mode(
    registry_mode: str,
) -> tuple[str, str]:
    """
    Registry Mode를 표준 Configuration Mode로 변환합니다.
    """

    normalized_mode = registry_mode.strip().upper()

    mapping = {
        "ACTIVE": (
            "ACTIVE",
            "운영 전략 설정",
        ),
        "PAPER_TRADING": (
            "PAPER_TRADING",
            "모의투자 전략 설정",
        ),
        "BASELINE": (
            "BASELINE",
            "기준 전략 설정",
        ),
        "RESEARCH_ONLY": (
            "RESEARCH_ONLY",
            "연구 전용 설정",
        ),
        "UNREGISTERED": (
            "UNAVAILABLE",
            "사용 가능한 전략 없음",
        ),
    }

    return mapping.get(
        normalized_mode,
        (
            "UNAVAILABLE",
            "사용 가능한 전략 없음",
        ),
    )


def resolve_parameter(
    payload: dict[str, Any],
    field_name: str,
    default_value: float | int,
) -> tuple[float | int, bool]:
    """
    Registry의 파라미터를 읽습니다.

    값이 없거나 잘못된 경우 기본값을 사용합니다.
    """

    raw_value = payload.get(
        field_name
    )

    if isinstance(
        default_value,
        int,
    ):
        converted = safe_int(
            raw_value
        )
    else:
        converted = safe_float(
            raw_value
        )

    if converted is None:
        return (
            default_value,
            True,
        )

    return (
        converted,
        False,
    )


def validate_parameters(
    entry_score: float,
    exit_score: float,
    stop_atr_multiple: float,
    target_atr_multiple: float,
    maximum_holding_days: int,
    position_percent: float,
) -> None:
    """
    전략 파라미터 값의 범위를 검사합니다.
    """

    if not 0.0 < entry_score <= 100.0:
        raise ValueError(
            f"Entry Score가 올바르지 않습니다: "
            f"{entry_score}"
        )

    if not 0.0 <= exit_score <= 100.0:
        raise ValueError(
            f"Exit Score가 올바르지 않습니다: "
            f"{exit_score}"
        )

    if exit_score >= entry_score:
        raise ValueError(
            "Exit Score는 Entry Score보다 "
            "낮아야 합니다."
        )

    if stop_atr_multiple <= 0.0:
        raise ValueError(
            "Stop ATR Multiple은 0보다 커야 합니다."
        )

    if target_atr_multiple <= 0.0:
        raise ValueError(
            "Target ATR Multiple은 0보다 커야 합니다."
        )

    if maximum_holding_days <= 0:
        raise ValueError(
            "Maximum Holding Days는 0보다 커야 합니다."
        )

    if not 0.0 < position_percent <= 100.0:
        raise ValueError(
            "Position Percent는 0보다 크고 "
            "100 이하여야 합니다."
        )


def build_configuration_notes(
    configuration_mode: str,
    fallback_used: bool,
    execution_enabled: bool,
    paper_execution_enabled: bool,
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    Configuration 상태에 따른 설명을 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if configuration_mode == "ACTIVE":
        reasons.append(
            "V8.6 Registry의 운영 전략 설정을 불러왔습니다."
        )

        next_actions.extend(
            [
                "실제 주문 연결 전 수동 승인 절차를 확인합니다.",
                "운영 전략 설정 파일의 변경 이력을 보관합니다.",
                "시장 데이터와 전략 설정의 Symbol을 확인합니다.",
            ]
        )

    elif configuration_mode == "PAPER_TRADING":
        reasons.append(
            "V8.6 Registry의 모의투자 전략 설정을 "
            "불러왔습니다."
        )

        next_actions.extend(
            [
                "모의투자 엔진에만 이 설정을 전달합니다.",
                "실제 주문 실행은 비활성 상태로 유지합니다.",
                "모의투자 성과를 별도의 파일에 기록합니다.",
            ]
        )

    elif configuration_mode == "BASELINE":
        reasons.append(
            "최근 전략 평가 결과에 따라 기준 전략 설정을 "
            "유지합니다."
        )

        next_actions.extend(
            [
                "기준 전략을 백테스트와 일일 분석에 사용합니다.",
                "자동 주문 실행은 비활성 상태로 유지합니다.",
                "새로운 데이터 누적 후 후보 전략을 다시 평가합니다.",
            ]
        )

    elif configuration_mode == "RESEARCH_ONLY":
        reasons.append(
            "현재 설정은 연구 및 백테스트 전용입니다."
        )

        next_actions.extend(
            [
                "실제 주문 또는 모의 주문에 연결하지 않습니다.",
                "추가 Walk-Forward 검증을 수행합니다.",
                "검증 통과 후 Registry 상태를 다시 확인합니다.",
            ]
        )

    else:
        warnings.append(
            "사용할 수 있는 Registry 전략이 없습니다."
        )

        next_actions.extend(
            [
                "V8.5와 V8.6 단계를 먼저 실행합니다.",
                "Registry Latest JSON 파일을 확인합니다.",
            ]
        )

    if fallback_used:
        warnings.append(
            "일부 파라미터가 없어 기본 기준값을 사용했습니다."
        )

    if execution_enabled:
        warnings.append(
            "Registry의 Execution Enabled 값은 "
            "무시되었습니다."
        )

    if paper_execution_enabled:
        warnings.append(
            "모의투자 실행은 별도의 모의투자 모듈에서만 "
            "허용해야 합니다."
        )

    warnings.append(
        "이 Configuration Loader는 전략 설정만 읽으며 "
        "실제 증권 주문을 실행하지 않습니다."
    )

    return (
        reasons,
        warnings,
        next_actions,
    )


def run_strategy_configuration_loader(
    symbol: str = "AAPL",
    source_file: str | Path | None = None,
) -> StrategyConfiguration:
    """
    V8.6 Registry를 읽고 표준 전략 설정을 생성합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if source_file is None:
        registry_path = find_latest_registry_file(
            normalized_symbol
        )
    else:
        registry_path = Path(
            source_file
        )

    registry_payload = load_json_file(
        registry_path
    )

    validate_registry_payload(
        registry_payload
    )

    registry_symbol = normalize_symbol(
        str(
            registry_payload.get(
                "symbol",
                "",
            )
        )
    )

    if registry_symbol != normalized_symbol:
        raise ValueError(
            "요청한 Symbol과 Registry Symbol이 "
            "일치하지 않습니다."
        )

    registry_mode = str(
        registry_payload.get(
            "registry_mode",
            "UNREGISTERED",
        )
    ).upper()

    (
        configuration_mode,
        configuration_label,
    ) = determine_configuration_mode(
        registry_mode
    )

    fallback_fields: list[str] = []

    (
        entry_score,
        entry_fallback,
    ) = resolve_parameter(
        registry_payload,
        "entry_score",
        DEFAULT_BASELINE_PARAMETERS[
            "entry_score"
        ],
    )

    if entry_fallback:
        fallback_fields.append(
            "entry_score"
        )

    (
        exit_score,
        exit_fallback,
    ) = resolve_parameter(
        registry_payload,
        "exit_score",
        DEFAULT_BASELINE_PARAMETERS[
            "exit_score"
        ],
    )

    if exit_fallback:
        fallback_fields.append(
            "exit_score"
        )

    (
        stop_atr_multiple,
        stop_fallback,
    ) = resolve_parameter(
        registry_payload,
        "stop_atr_multiple",
        DEFAULT_BASELINE_PARAMETERS[
            "stop_atr_multiple"
        ],
    )

    if stop_fallback:
        fallback_fields.append(
            "stop_atr_multiple"
        )

    (
        target_atr_multiple,
        target_fallback,
    ) = resolve_parameter(
        registry_payload,
        "target_atr_multiple",
        DEFAULT_BASELINE_PARAMETERS[
            "target_atr_multiple"
        ],
    )

    if target_fallback:
        fallback_fields.append(
            "target_atr_multiple"
        )

    (
        maximum_holding_days,
        holding_fallback,
    ) = resolve_parameter(
        registry_payload,
        "maximum_holding_days",
        DEFAULT_BASELINE_PARAMETERS[
            "maximum_holding_days"
        ],
    )

    if holding_fallback:
        fallback_fields.append(
            "maximum_holding_days"
        )

    (
        position_percent,
        position_fallback,
    ) = resolve_parameter(
        registry_payload,
        "position_percent",
        DEFAULT_BASELINE_PARAMETERS[
            "position_percent"
        ],
    )

    if position_fallback:
        fallback_fields.append(
            "position_percent"
        )

    entry_score = float(
        entry_score
    )

    exit_score = float(
        exit_score
    )

    stop_atr_multiple = float(
        stop_atr_multiple
    )

    target_atr_multiple = float(
        target_atr_multiple
    )

    maximum_holding_days = int(
        maximum_holding_days
    )

    position_percent = float(
        position_percent
    )

    validate_parameters(
        entry_score=entry_score,
        exit_score=exit_score,
        stop_atr_multiple=stop_atr_multiple,
        target_atr_multiple=target_atr_multiple,
        maximum_holding_days=maximum_holding_days,
        position_percent=position_percent,
    )

    registry_ready = safe_bool(
        registry_payload.get(
            "registry_ready"
        )
    )

    configuration_ready = (
        registry_ready
        and configuration_mode
        != "UNAVAILABLE"
    )

    # 실제 주문은 어떤 Registry 상태에서도
    # 자동 활성화하지 않습니다.
    execution_enabled = False

    paper_execution_enabled = (
        configuration_mode
        == "PAPER_TRADING"
        and configuration_ready
    )

    manual_approval_required = True

    fallback_used = bool(
        fallback_fields
    )

    (
        reasons,
        warnings,
        next_actions,
    ) = build_configuration_notes(
        configuration_mode=configuration_mode,
        fallback_used=fallback_used,
        execution_enabled=safe_bool(
            registry_payload.get(
                "execution_enabled"
            )
        ),
        paper_execution_enabled=(
            paper_execution_enabled
        ),
    )

    if fallback_fields:
        warnings.append(
            "기본값이 사용된 항목: "
            + ", ".join(
                fallback_fields
            )
        )

    result = StrategyConfiguration(
        version="V8.7",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        source_registry_file=str(
            registry_path
        ),

        registry_mode=registry_mode,
        configuration_mode=(
            configuration_mode
        ),
        configuration_label=(
            configuration_label
        ),

        strategy_source=str(
            registry_payload.get(
                "selected_strategy_source",
                "NONE",
            )
        ),

        strategy_status=str(
            registry_payload.get(
                "selected_strategy_status",
                "UNREGISTERED",
            )
        ),

        strategy_name=(
            str(
                registry_payload.get(
                    "selected_strategy_name"
                )
            )
            if registry_payload.get(
                "selected_strategy_name"
            )
            is not None
            else None
        ),

        strategy_type=(
            str(
                registry_payload.get(
                    "selected_strategy_type"
                )
            )
            if registry_payload.get(
                "selected_strategy_type"
            )
            is not None
            else None
        ),

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
        position_percent=position_percent,

        candidate_score=safe_float(
            registry_payload.get(
                "candidate_score"
            )
        ),

        baseline_score=safe_float(
            registry_payload.get(
                "baseline_score"
            )
        ),

        score_improvement=safe_float(
            registry_payload.get(
                "score_improvement"
            )
        ),

        confidence_score=safe_float(
            registry_payload.get(
                "confidence_score"
            )
        ),

        confidence_level=str(
            registry_payload.get(
                "confidence_level",
                "UNKNOWN",
            )
            or "UNKNOWN"
        ),

        risk_score=safe_float(
            registry_payload.get(
                "risk_score"
            )
        ),

        risk_level=str(
            registry_payload.get(
                "risk_level",
                "UNKNOWN",
            )
            or "UNKNOWN"
        ),

        recommendation_strength=safe_int(
            registry_payload.get(
                "recommendation_strength"
            )
        ),

        registry_ready=registry_ready,
        configuration_ready=(
            configuration_ready
        ),

        execution_enabled=(
            execution_enabled
        ),

        paper_execution_enabled=(
            paper_execution_enabled
        ),

        manual_approval_required=(
            manual_approval_required
        ),

        is_default_configuration=(
            configuration_mode
            == "BASELINE"
        ),

        fallback_used=fallback_used,

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_strategy_configuration(
        result
    )

    return result


def save_strategy_configuration(
    result: StrategyConfiguration,
) -> tuple[Path, Path]:
    """
    전략 Configuration을 JSON으로 저장합니다.
    """

    CONFIGURATION_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        CONFIGURATION_DIRECTORY
        / (
            f"{result.symbol}_"
            "strategy_configuration_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        CONFIGURATION_DIRECTORY
        / (
            f"{result.symbol}_"
            "strategy_configuration_latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    payload = result.to_dict()

    write_json_file(
        report_path,
        payload,
    )

    write_json_file(
        latest_path,
        payload,
    )

    return (
        report_path,
        latest_path,
    )


def format_optional_number(
    value: float | int | None,
    decimal_places: int = 2,
) -> str:
    """
    None일 수 있는 숫자를 출력용 문자열로 변환합니다.
    """

    if value is None:
        return "None"

    if isinstance(
        value,
        int,
    ):
        return str(value)

    return f"{value:.{decimal_places}f}"


def print_strategy_configuration(
    result: StrategyConfiguration,
) -> None:
    """
    V8.7 전략 설정을 출력합니다.
    """

    print()
    print("=" * 135)
    print(
        f"{result.symbol} V8.7 "
        "STRATEGY CONFIGURATION LOADER"
    )
    print("=" * 135)

    print(
        f"Registry mode                : "
        f"{result.registry_mode}"
    )

    print(
        f"Configuration mode           : "
        f"{result.configuration_mode}"
    )

    print(
        f"Configuration label          : "
        f"{result.configuration_label}"
    )

    print(
        f"Registry ready               : "
        f"{result.registry_ready}"
    )

    print(
        f"Configuration ready          : "
        f"{result.configuration_ready}"
    )

    print()
    print("STRATEGY")
    print("-" * 135)

    print(
        f"Strategy source              : "
        f"{result.strategy_source}"
    )

    print(
        f"Strategy status              : "
        f"{result.strategy_status}"
    )

    print(
        f"Strategy name                : "
        f"{result.strategy_name}"
    )

    print(
        f"Strategy type                : "
        f"{result.strategy_type}"
    )

    print()
    print("PARAMETERS")
    print("-" * 135)

    print(
        f"Entry score                  : "
        f"{result.entry_score:.2f}"
    )

    print(
        f"Exit score                   : "
        f"{result.exit_score:.2f}"
    )

    print(
        f"Stop ATR                     : "
        f"{result.stop_atr_multiple:.2f}"
    )

    print(
        f"Target ATR                   : "
        f"{result.target_atr_multiple:.2f}"
    )

    print(
        f"Maximum holding days         : "
        f"{result.maximum_holding_days}"
    )

    print(
        f"Position percent             : "
        f"{result.position_percent:.2f}%"
    )

    print()
    print("EVALUATION")
    print("-" * 135)

    print(
        f"Candidate score              : "
        f"{format_optional_number(result.candidate_score)}/100"
    )

    print(
        f"Baseline score               : "
        f"{format_optional_number(result.baseline_score)}/100"
    )

    improvement_text = (
        "None"
        if result.score_improvement is None
        else f"{result.score_improvement:+.2f} points"
    )

    print(
        f"Score improvement            : "
        f"{improvement_text}"
    )

    print(
        f"Confidence                   : "
        f"{format_optional_number(result.confidence_score)}/100 "
        f"({result.confidence_level})"
    )

    print(
        f"Risk                         : "
        f"{format_optional_number(result.risk_score)}/100 "
        f"({result.risk_level})"
    )

    print(
        f"Recommendation strength      : "
        f"{format_optional_number(result.recommendation_strength)}/5"
    )

    print()
    print("SAFETY")
    print("-" * 135)

    print(
        f"Execution enabled            : "
        f"{result.execution_enabled}"
    )

    print(
        f"Paper execution enabled      : "
        f"{result.paper_execution_enabled}"
    )

    print(
        f"Manual approval required     : "
        f"{result.manual_approval_required}"
    )

    print(
        f"Default configuration        : "
        f"{result.is_default_configuration}"
    )

    print(
        f"Fallback used                : "
        f"{result.fallback_used}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 135)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * 135)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * 135)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 135)

    print(
        f"Source Registry file         : "
        f"{result.source_registry_file}"
    )

    print(
        f"Report file                  : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                  : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 135)

    print(
        "주의: 이 Loader는 전략 설정을 제공하지만 "
        "실제 주문을 생성하거나 증권사로 전송하지 않습니다."
    )