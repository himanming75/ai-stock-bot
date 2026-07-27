import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIGURATION_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "configurations"
)

RUNTIME_GUARD_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "runtime_guard"
)


VALID_CONFIGURATION_MODES = {
    "ACTIVE",
    "PAPER_TRADING",
    "BASELINE",
    "RESEARCH_ONLY",
    "UNAVAILABLE",
}


VALID_RUNTIME_MODES = {
    "LIVE_READY",
    "PAPER_READY",
    "ANALYSIS_ONLY",
    "RESEARCH_ONLY",
    "BLOCKED",
}


VALID_GUARD_STATUSES = {
    "PASSED",
    "RESTRICTED",
    "BLOCKED",
    "FAILED",
}


DEFAULT_MAX_POSITION_PERCENT = 25.0
DEFAULT_MAX_HOLDING_DAYS = 90
DEFAULT_MIN_STOP_ATR = 0.50
DEFAULT_MAX_STOP_ATR = 5.00
DEFAULT_MIN_TARGET_ATR = 0.50
DEFAULT_MAX_TARGET_ATR = 10.00


@dataclass
class StrategyRuntimeGuardResult:
    """
    V8.8 전략 실행 안전 점검 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_configuration_file: str

    configuration_mode: str
    configuration_ready: bool

    runtime_mode: str
    runtime_label: str
    guard_status: str

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

    analysis_allowed: bool
    backtest_allowed: bool
    research_allowed: bool
    paper_execution_allowed: bool
    live_execution_allowed: bool

    execution_enabled_from_configuration: bool
    paper_execution_enabled_from_configuration: bool
    manual_approval_required: bool

    parameter_checks_passed: bool
    execution_checks_passed: bool
    source_checks_passed: bool
    all_checks_passed: bool

    live_execution_blocked: bool
    paper_execution_blocked: bool

    blocking_reasons: list[str]
    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

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


def find_latest_configuration_file(
    symbol: str,
) -> Path:
    """
    최신 V8.7 Configuration 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    expected_path = (
        CONFIGURATION_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "strategy_configuration_latest.json"
        )
    )

    if expected_path.exists():
        return expected_path

    if not CONFIGURATION_DIRECTORY.exists():
        raise FileNotFoundError(
            "V8.7 Configuration 폴더가 없습니다: "
            f"{CONFIGURATION_DIRECTORY}"
        )

    matching_files = [
        path
        for path in CONFIGURATION_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "strategy_configuration_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not matching_files:
        raise FileNotFoundError(
            f"{normalized_symbol} V8.7 Configuration "
            "파일을 찾을 수 없습니다."
        )

    return max(
        matching_files,
        key=lambda path: path.stat().st_mtime,
    )


def validate_configuration_payload(
    payload: dict[str, Any],
) -> None:
    """
    V8.7 Configuration 데이터의 필수 항목을 검사합니다.
    """

    required_keys = {
        "version",
        "symbol",
        "configuration_mode",
        "configuration_ready",
        "strategy_source",
        "strategy_status",
        "strategy_name",
        "strategy_type",
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
        "execution_enabled",
        "paper_execution_enabled",
        "manual_approval_required",
    }

    missing_keys = (
        required_keys
        - set(payload.keys())
    )

    if missing_keys:
        raise ValueError(
            "V8.7 Configuration 데이터에 "
            "필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    version = str(
        payload.get(
            "version",
            "",
        )
    ).upper()

    if version != "V8.7":
        raise ValueError(
            "V8.7 Configuration 파일이 아닙니다: "
            f"{version}"
        )

    configuration_mode = str(
        payload.get(
            "configuration_mode",
            "",
        )
    ).upper()

    if (
        configuration_mode
        not in VALID_CONFIGURATION_MODES
    ):
        raise ValueError(
            "올바르지 않은 Configuration Mode입니다: "
            f"{configuration_mode}"
        )


def determine_runtime_mode(
    configuration_mode: str,
    configuration_ready: bool,
    execution_enabled: bool,
    paper_execution_enabled: bool,
    manual_approval_required: bool,
) -> tuple[str, str]:
    """
    Configuration 상태를 Runtime Mode로 변환합니다.
    """

    normalized_mode = (
        configuration_mode
        .strip()
        .upper()
    )

    if not configuration_ready:
        return (
            "BLOCKED",
            "실행 차단",
        )

    if normalized_mode == "ACTIVE":
        if (
            execution_enabled
            and not manual_approval_required
        ):
            return (
                "LIVE_READY",
                "실거래 준비",
            )

        return (
            "ANALYSIS_ONLY",
            "운영 전략 분석 전용",
        )

    if normalized_mode == "PAPER_TRADING":
        if paper_execution_enabled:
            return (
                "PAPER_READY",
                "모의투자 준비",
            )

        return (
            "ANALYSIS_ONLY",
            "모의투자 설정 분석 전용",
        )

    if normalized_mode == "BASELINE":
        return (
            "ANALYSIS_ONLY",
            "기준 전략 분석 전용",
        )

    if normalized_mode == "RESEARCH_ONLY":
        return (
            "RESEARCH_ONLY",
            "연구 및 백테스트 전용",
        )

    return (
        "BLOCKED",
        "실행 가능한 전략 없음",
    )


def validate_runtime_parameters(
    entry_score: float,
    exit_score: float,
    stop_atr_multiple: float,
    target_atr_multiple: float,
    maximum_holding_days: int,
    position_percent: float,
) -> tuple[
    bool,
    list[str],
]:
    """
    실행 전 전략 파라미터의 안전 범위를 검사합니다.
    """

    errors: list[str] = []

    if not 0.0 < entry_score <= 100.0:
        errors.append(
            "Entry Score가 0보다 크고 "
            "100 이하여야 합니다."
        )

    if not 0.0 <= exit_score <= 100.0:
        errors.append(
            "Exit Score가 0 이상 "
            "100 이하여야 합니다."
        )

    if exit_score >= entry_score:
        errors.append(
            "Exit Score는 Entry Score보다 "
            "낮아야 합니다."
        )

    if not (
        DEFAULT_MIN_STOP_ATR
        <= stop_atr_multiple
        <= DEFAULT_MAX_STOP_ATR
    ):
        errors.append(
            "Stop ATR이 허용 범위를 벗어났습니다: "
            f"{DEFAULT_MIN_STOP_ATR}~"
            f"{DEFAULT_MAX_STOP_ATR}"
        )

    if not (
        DEFAULT_MIN_TARGET_ATR
        <= target_atr_multiple
        <= DEFAULT_MAX_TARGET_ATR
    ):
        errors.append(
            "Target ATR이 허용 범위를 벗어났습니다: "
            f"{DEFAULT_MIN_TARGET_ATR}~"
            f"{DEFAULT_MAX_TARGET_ATR}"
        )

    if maximum_holding_days <= 0:
        errors.append(
            "Maximum Holding Days는 "
            "0보다 커야 합니다."
        )

    if (
        maximum_holding_days
        > DEFAULT_MAX_HOLDING_DAYS
    ):
        errors.append(
            "Maximum Holding Days가 "
            f"{DEFAULT_MAX_HOLDING_DAYS}일을 "
            "초과했습니다."
        )

    if not (
        0.0
        < position_percent
        <= DEFAULT_MAX_POSITION_PERCENT
    ):
        errors.append(
            "Position Percent가 허용 범위를 "
            "벗어났습니다: "
            f"0 초과~{DEFAULT_MAX_POSITION_PERCENT}%"
        )

    return (
        not errors,
        errors,
    )


def evaluate_runtime_permissions(
    runtime_mode: str,
) -> dict[str, bool]:
    """
    Runtime Mode에 따른 허용 작업을 결정합니다.
    """

    normalized_mode = (
        runtime_mode
        .strip()
        .upper()
    )

    if normalized_mode == "LIVE_READY":
        return {
            "analysis_allowed": True,
            "backtest_allowed": True,
            "research_allowed": True,
            "paper_execution_allowed": True,
            "live_execution_allowed": True,
        }

    if normalized_mode == "PAPER_READY":
        return {
            "analysis_allowed": True,
            "backtest_allowed": True,
            "research_allowed": True,
            "paper_execution_allowed": True,
            "live_execution_allowed": False,
        }

    if normalized_mode == "ANALYSIS_ONLY":
        return {
            "analysis_allowed": True,
            "backtest_allowed": True,
            "research_allowed": True,
            "paper_execution_allowed": False,
            "live_execution_allowed": False,
        }

    if normalized_mode == "RESEARCH_ONLY":
        return {
            "analysis_allowed": True,
            "backtest_allowed": True,
            "research_allowed": True,
            "paper_execution_allowed": False,
            "live_execution_allowed": False,
        }

    return {
        "analysis_allowed": False,
        "backtest_allowed": False,
        "research_allowed": False,
        "paper_execution_allowed": False,
        "live_execution_allowed": False,
    }


def determine_guard_status(
    runtime_mode: str,
    all_checks_passed: bool,
) -> str:
    """
    전체 점검 결과를 Guard Status로 변환합니다.
    """

    if not all_checks_passed:
        return "FAILED"

    if runtime_mode == "BLOCKED":
        return "BLOCKED"

    if runtime_mode in {
        "ANALYSIS_ONLY",
        "RESEARCH_ONLY",
        "PAPER_READY",
    }:
        return "RESTRICTED"

    return "PASSED"


def build_runtime_notes(
    configuration_mode: str,
    runtime_mode: str,
    parameter_errors: list[str],
    manual_approval_required: bool,
) -> tuple[
    list[str],
    list[str],
    list[str],
    list[str],
]:
    """
    Runtime Guard의 설명과 경고를 생성합니다.
    """

    blocking_reasons: list[str] = []
    reasons: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if parameter_errors:
        blocking_reasons.extend(
            parameter_errors
        )

    if runtime_mode == "LIVE_READY":
        reasons.append(
            "운영 전략의 실거래 실행 조건을 "
            "통과했습니다."
        )

        warnings.append(
            "실거래 연결 전 별도의 사용자 승인과 "
            "증권사 연결 검증이 필요합니다."
        )

        next_actions.extend(
            [
                "주문 수량 제한을 다시 확인합니다.",
                "시장 운영 시간과 계좌 상태를 확인합니다.",
                "최종 수동 승인 후에만 주문 모듈을 연결합니다.",
            ]
        )

    elif runtime_mode == "PAPER_READY":
        reasons.append(
            "모의투자 실행 조건을 통과했습니다."
        )

        warnings.append(
            "실제 주문 실행은 허용되지 않습니다."
        )

        next_actions.extend(
            [
                "모의투자 계좌에서만 실행합니다.",
                "체결 로그와 포지션 기록을 저장합니다.",
                "실제 증권사 주문 모듈과 분리합니다.",
            ]
        )

    elif runtime_mode == "ANALYSIS_ONLY":
        reasons.append(
            "현재 전략은 분석과 백테스트에만 "
            "사용할 수 있습니다."
        )

        blocking_reasons.append(
            "현재 Configuration Mode에서는 "
            "실제 주문과 모의 주문이 차단됩니다."
        )

        next_actions.extend(
            [
                "분석 및 백테스트에만 설정을 사용합니다.",
                "실제 주문 모듈에는 전달하지 않습니다.",
                "전략 승격 상태가 변경되면 다시 검사합니다.",
            ]
        )

    elif runtime_mode == "RESEARCH_ONLY":
        reasons.append(
            "현재 전략은 연구와 백테스트 전용입니다."
        )

        blocking_reasons.append(
            "연구 전용 전략은 주문 실행에 "
            "사용할 수 없습니다."
        )

        next_actions.extend(
            [
                "추가 Walk-Forward 검증을 수행합니다.",
                "전략 승격 절차를 다시 실행합니다.",
                "실행 모듈과 연결하지 않습니다.",
            ]
        )

    else:
        blocking_reasons.append(
            "사용 가능한 전략 설정이 없거나 "
            "Configuration이 준비되지 않았습니다."
        )

        next_actions.extend(
            [
                "V8.6 Registry 상태를 확인합니다.",
                "V8.7 Configuration Loader를 다시 실행합니다.",
                "Configuration Latest 파일을 확인합니다.",
            ]
        )

    if manual_approval_required:
        warnings.append(
            "모든 주문 관련 작업에는 "
            "수동 승인이 필요합니다."
        )

    if configuration_mode == "BASELINE":
        reasons.append(
            "기준 전략 유지 상태이므로 "
            "자동 주문 실행을 허용하지 않습니다."
        )

    warnings.append(
        "이 Runtime Guard는 실행 권한을 판정하지만 "
        "실제 주문을 생성하거나 전송하지 않습니다."
    )

    return (
        blocking_reasons,
        reasons,
        warnings,
        next_actions,
    )


def run_strategy_runtime_guard(
    symbol: str = "AAPL",
    source_file: str | Path | None = None,
) -> StrategyRuntimeGuardResult:
    """
    V8.7 Configuration을 읽고
    실행 가능 범위를 최종 판정합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if source_file is None:
        configuration_path = (
            find_latest_configuration_file(
                normalized_symbol
            )
        )
    else:
        configuration_path = Path(
            source_file
        )

    configuration_payload = load_json_file(
        configuration_path
    )

    validate_configuration_payload(
        configuration_payload
    )

    configuration_symbol = normalize_symbol(
        str(
            configuration_payload.get(
                "symbol",
                "",
            )
        )
    )

    if configuration_symbol != normalized_symbol:
        raise ValueError(
            "요청한 Symbol과 Configuration Symbol이 "
            "일치하지 않습니다."
        )

    configuration_mode = str(
        configuration_payload.get(
            "configuration_mode",
            "UNAVAILABLE",
        )
    ).upper()

    configuration_ready = safe_bool(
        configuration_payload.get(
            "configuration_ready"
        )
    )

    execution_enabled = safe_bool(
        configuration_payload.get(
            "execution_enabled"
        )
    )

    paper_execution_enabled = safe_bool(
        configuration_payload.get(
            "paper_execution_enabled"
        )
    )

    manual_approval_required = safe_bool(
        configuration_payload.get(
            "manual_approval_required"
        ),
        default=True,
    )

    entry_score = safe_float(
        configuration_payload.get(
            "entry_score"
        )
    )

    exit_score = safe_float(
        configuration_payload.get(
            "exit_score"
        )
    )

    stop_atr_multiple = safe_float(
        configuration_payload.get(
            "stop_atr_multiple"
        )
    )

    target_atr_multiple = safe_float(
        configuration_payload.get(
            "target_atr_multiple"
        )
    )

    maximum_holding_days = safe_int(
        configuration_payload.get(
            "maximum_holding_days"
        )
    )

    position_percent = safe_float(
        configuration_payload.get(
            "position_percent"
        )
    )

    missing_values = []

    if entry_score is None:
        missing_values.append(
            "entry_score"
        )

    if exit_score is None:
        missing_values.append(
            "exit_score"
        )

    if stop_atr_multiple is None:
        missing_values.append(
            "stop_atr_multiple"
        )

    if target_atr_multiple is None:
        missing_values.append(
            "target_atr_multiple"
        )

    if maximum_holding_days is None:
        missing_values.append(
            "maximum_holding_days"
        )

    if position_percent is None:
        missing_values.append(
            "position_percent"
        )

    if missing_values:
        raise ValueError(
            "Configuration에 필수 파라미터가 없습니다: "
            + ", ".join(
                missing_values
            )
        )

    (
        parameter_checks_passed,
        parameter_errors,
    ) = validate_runtime_parameters(
        entry_score=float(entry_score),
        exit_score=float(exit_score),
        stop_atr_multiple=float(
            stop_atr_multiple
        ),
        target_atr_multiple=float(
            target_atr_multiple
        ),
        maximum_holding_days=int(
            maximum_holding_days
        ),
        position_percent=float(
            position_percent
        ),
    )

    (
        runtime_mode,
        runtime_label,
    ) = determine_runtime_mode(
        configuration_mode=configuration_mode,
        configuration_ready=configuration_ready,
        execution_enabled=execution_enabled,
        paper_execution_enabled=(
            paper_execution_enabled
        ),
        manual_approval_required=(
            manual_approval_required
        ),
    )

    permissions = evaluate_runtime_permissions(
        runtime_mode
    )

    source_checks_passed = (
        configuration_path.exists()
        and configuration_symbol
        == normalized_symbol
        and configuration_mode
        in VALID_CONFIGURATION_MODES
    )

    execution_checks_passed = True

    if permissions[
        "live_execution_allowed"
    ]:
        execution_checks_passed = (
            configuration_mode == "ACTIVE"
            and execution_enabled
            and not manual_approval_required
        )

    if permissions[
        "paper_execution_allowed"
    ]:
        execution_checks_passed = (
            execution_checks_passed
            and configuration_mode
            == "PAPER_TRADING"
            and paper_execution_enabled
        )

    all_checks_passed = (
        source_checks_passed
        and parameter_checks_passed
        and execution_checks_passed
    )

    guard_status = determine_guard_status(
        runtime_mode=runtime_mode,
        all_checks_passed=all_checks_passed,
    )

    (
        blocking_reasons,
        reasons,
        warnings,
        next_actions,
    ) = build_runtime_notes(
        configuration_mode=configuration_mode,
        runtime_mode=runtime_mode,
        parameter_errors=parameter_errors,
        manual_approval_required=(
            manual_approval_required
        ),
    )

    live_execution_allowed = permissions[
        "live_execution_allowed"
    ]

    paper_execution_allowed = permissions[
        "paper_execution_allowed"
    ]

    result = StrategyRuntimeGuardResult(
        version="V8.8",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        source_configuration_file=str(
            configuration_path
        ),

        configuration_mode=(
            configuration_mode
        ),

        configuration_ready=(
            configuration_ready
        ),

        runtime_mode=runtime_mode,
        runtime_label=runtime_label,
        guard_status=guard_status,

        strategy_source=str(
            configuration_payload.get(
                "strategy_source",
                "NONE",
            )
        ),

        strategy_status=str(
            configuration_payload.get(
                "strategy_status",
                "UNREGISTERED",
            )
        ),

        strategy_name=(
            str(
                configuration_payload.get(
                    "strategy_name"
                )
            )
            if configuration_payload.get(
                "strategy_name"
            )
            is not None
            else None
        ),

        strategy_type=(
            str(
                configuration_payload.get(
                    "strategy_type"
                )
            )
            if configuration_payload.get(
                "strategy_type"
            )
            is not None
            else None
        ),

        entry_score=float(
            entry_score
        ),

        exit_score=float(
            exit_score
        ),

        stop_atr_multiple=float(
            stop_atr_multiple
        ),

        target_atr_multiple=float(
            target_atr_multiple
        ),

        maximum_holding_days=int(
            maximum_holding_days
        ),

        position_percent=float(
            position_percent
        ),

        analysis_allowed=permissions[
            "analysis_allowed"
        ],

        backtest_allowed=permissions[
            "backtest_allowed"
        ],

        research_allowed=permissions[
            "research_allowed"
        ],

        paper_execution_allowed=(
            paper_execution_allowed
        ),

        live_execution_allowed=(
            live_execution_allowed
        ),

        execution_enabled_from_configuration=(
            execution_enabled
        ),

        paper_execution_enabled_from_configuration=(
            paper_execution_enabled
        ),

        manual_approval_required=(
            manual_approval_required
        ),

        parameter_checks_passed=(
            parameter_checks_passed
        ),

        execution_checks_passed=(
            execution_checks_passed
        ),

        source_checks_passed=(
            source_checks_passed
        ),

        all_checks_passed=(
            all_checks_passed
        ),

        live_execution_blocked=(
            not live_execution_allowed
        ),

        paper_execution_blocked=(
            not paper_execution_allowed
        ),

        blocking_reasons=(
            blocking_reasons
        ),

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_strategy_runtime_guard(
        result
    )

    return result


def save_strategy_runtime_guard(
    result: StrategyRuntimeGuardResult,
) -> tuple[Path, Path]:
    """
    Runtime Guard 결과를 JSON으로 저장합니다.
    """

    RUNTIME_GUARD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        RUNTIME_GUARD_DIRECTORY
        / (
            f"{result.symbol}_"
            "strategy_runtime_guard_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        RUNTIME_GUARD_DIRECTORY
        / (
            f"{result.symbol}_"
            "strategy_runtime_guard_latest.json"
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


def print_strategy_runtime_guard(
    result: StrategyRuntimeGuardResult,
) -> None:
    """
    V8.8 Runtime Guard 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V8.8 "
        "STRATEGY RUNTIME GUARD"
    )
    print("=" * 140)

    print(
        f"Configuration mode             : "
        f"{result.configuration_mode}"
    )

    print(
        f"Configuration ready            : "
        f"{result.configuration_ready}"
    )

    print(
        f"Runtime mode                   : "
        f"{result.runtime_mode}"
    )

    print(
        f"Runtime label                  : "
        f"{result.runtime_label}"
    )

    print(
        f"Guard status                   : "
        f"{result.guard_status}"
    )

    print()
    print("STRATEGY")
    print("-" * 140)

    print(
        f"Strategy source                : "
        f"{result.strategy_source}"
    )

    print(
        f"Strategy status                : "
        f"{result.strategy_status}"
    )

    print(
        f"Strategy name                  : "
        f"{result.strategy_name}"
    )

    print(
        f"Strategy type                  : "
        f"{result.strategy_type}"
    )

    print()
    print("PARAMETERS")
    print("-" * 140)

    print(
        f"Entry score                    : "
        f"{result.entry_score:.2f}"
    )

    print(
        f"Exit score                     : "
        f"{result.exit_score:.2f}"
    )

    print(
        f"Stop ATR                       : "
        f"{result.stop_atr_multiple:.2f}"
    )

    print(
        f"Target ATR                     : "
        f"{result.target_atr_multiple:.2f}"
    )

    print(
        f"Maximum holding days           : "
        f"{result.maximum_holding_days}"
    )

    print(
        f"Position percent               : "
        f"{result.position_percent:.2f}%"
    )

    print()
    print("PERMISSIONS")
    print("-" * 140)

    print(
        f"Analysis allowed               : "
        f"{result.analysis_allowed}"
    )

    print(
        f"Backtest allowed               : "
        f"{result.backtest_allowed}"
    )

    print(
        f"Research allowed               : "
        f"{result.research_allowed}"
    )

    print(
        f"Paper execution allowed        : "
        f"{result.paper_execution_allowed}"
    )

    print(
        f"Live execution allowed         : "
        f"{result.live_execution_allowed}"
    )

    print()
    print("SAFETY")
    print("-" * 140)

    print(
        f"Live execution blocked         : "
        f"{result.live_execution_blocked}"
    )

    print(
        f"Paper execution blocked        : "
        f"{result.paper_execution_blocked}"
    )

    print(
        f"Manual approval required       : "
        f"{result.manual_approval_required}"
    )

    print(
        f"Parameter checks passed        : "
        f"{result.parameter_checks_passed}"
    )

    print(
        f"Execution checks passed        : "
        f"{result.execution_checks_passed}"
    )

    print(
        f"Source checks passed           : "
        f"{result.source_checks_passed}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    if result.blocking_reasons:
        print()
        print("BLOCKING REASONS")
        print("-" * 140)

        for reason in result.blocking_reasons:
            print(
                f"- {reason}"
            )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 140)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * 140)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * 140)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Configuration file      : "
        f"{result.source_configuration_file}"
    )

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 140)

    print(
        "주의: Runtime Guard는 실행 가능 여부만 판정하며 "
        "실제 증권 주문을 생성하거나 전송하지 않습니다."
    )