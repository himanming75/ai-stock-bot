import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RUNTIME_GUARD_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "runtime_guard"
)

RUNTIME_PROVIDER_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_management"
    / "runtime_provider"
)


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


VALID_PROVIDER_STATUSES = {
    "READY",
    "LIMITED",
    "BLOCKED",
    "FAILED",
}


VALID_PROVIDER_PROFILES = {
    "LIVE",
    "PAPER",
    "ANALYSIS",
    "RESEARCH",
    "NONE",
}


@dataclass(frozen=True)
class RuntimeStrategyParameters:
    """
    Runtime에서 사용할 전략 파라미터입니다.

    frozen=True이므로 생성 후 값을 직접 변경할 수 없습니다.
    """

    entry_score: float
    exit_score: float
    stop_atr_multiple: float
    target_atr_multiple: float
    maximum_holding_days: int
    position_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyRuntimeConfiguration:
    """
    V8.9 최종 Runtime Configuration입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_runtime_guard_file: str

    provider_status: str
    provider_profile: str
    provider_label: str

    configuration_mode: str
    runtime_mode: str
    guard_status: str

    strategy_source: str
    strategy_status: str
    strategy_name: str | None
    strategy_type: str | None

    parameters: RuntimeStrategyParameters

    analysis_enabled: bool
    backtest_enabled: bool
    research_enabled: bool
    paper_execution_enabled: bool
    live_execution_enabled: bool

    live_execution_blocked: bool
    paper_execution_blocked: bool

    manual_approval_required: bool
    provider_ready: bool
    source_checks_passed: bool
    permission_checks_passed: bool
    parameter_checks_passed: bool
    all_checks_passed: bool

    allowed_operations: list[str]
    blocked_operations: list[str]

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["parameters"] = (
            self.parameters.to_dict()
        )

        return payload


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
    JSON 파일을 임시 파일을 이용하여 안전하게 저장합니다.
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


def find_latest_runtime_guard_file(
    symbol: str,
) -> Path:
    """
    최신 V8.8 Runtime Guard 파일을 찾습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    expected_path = (
        RUNTIME_GUARD_DIRECTORY
        / (
            f"{normalized_symbol}_"
            "strategy_runtime_guard_latest.json"
        )
    )

    if expected_path.exists():
        return expected_path

    if not RUNTIME_GUARD_DIRECTORY.exists():
        raise FileNotFoundError(
            "V8.8 Runtime Guard 폴더가 없습니다: "
            f"{RUNTIME_GUARD_DIRECTORY}"
        )

    matching_files = [
        path
        for path in RUNTIME_GUARD_DIRECTORY.glob(
            f"{normalized_symbol}_"
            "strategy_runtime_guard_*.json"
        )
        if "latest" not in path.name.lower()
    ]

    if not matching_files:
        raise FileNotFoundError(
            f"{normalized_symbol} V8.8 Runtime Guard "
            "파일을 찾을 수 없습니다."
        )

    return max(
        matching_files,
        key=lambda path: path.stat().st_mtime,
    )


def validate_runtime_guard_payload(
    payload: dict[str, Any],
) -> None:
    """
    V8.8 Runtime Guard JSON의 필수 항목을 검사합니다.
    """

    required_keys = {
        "version",
        "symbol",
        "configuration_mode",
        "runtime_mode",
        "guard_status",
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
        "analysis_allowed",
        "backtest_allowed",
        "research_allowed",
        "paper_execution_allowed",
        "live_execution_allowed",
        "live_execution_blocked",
        "paper_execution_blocked",
        "manual_approval_required",
        "parameter_checks_passed",
        "execution_checks_passed",
        "source_checks_passed",
        "all_checks_passed",
    }

    missing_keys = (
        required_keys
        - set(payload.keys())
    )

    if missing_keys:
        raise ValueError(
            "V8.8 Runtime Guard 데이터에 "
            "필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    version = str(
        payload.get(
            "version",
            "",
        )
    ).upper()

    if version != "V8.8":
        raise ValueError(
            "V8.8 Runtime Guard 파일이 아닙니다: "
            f"{version}"
        )

    runtime_mode = str(
        payload.get(
            "runtime_mode",
            "",
        )
    ).upper()

    if runtime_mode not in VALID_RUNTIME_MODES:
        raise ValueError(
            "올바르지 않은 Runtime Mode입니다: "
            f"{runtime_mode}"
        )

    guard_status = str(
        payload.get(
            "guard_status",
            "",
        )
    ).upper()

    if guard_status not in VALID_GUARD_STATUSES:
        raise ValueError(
            "올바르지 않은 Guard Status입니다: "
            f"{guard_status}"
        )


def validate_strategy_parameters(
    parameters: RuntimeStrategyParameters,
) -> tuple[
    bool,
    list[str],
]:
    """
    Runtime 파라미터를 다시 한번 검사합니다.
    """

    errors: list[str] = []

    if not 0.0 < parameters.entry_score <= 100.0:
        errors.append(
            "Entry Score가 허용 범위를 벗어났습니다."
        )

    if not 0.0 <= parameters.exit_score <= 100.0:
        errors.append(
            "Exit Score가 허용 범위를 벗어났습니다."
        )

    if (
        parameters.exit_score
        >= parameters.entry_score
    ):
        errors.append(
            "Exit Score는 Entry Score보다 "
            "낮아야 합니다."
        )

    if not 0.50 <= parameters.stop_atr_multiple <= 5.00:
        errors.append(
            "Stop ATR이 허용 범위를 벗어났습니다."
        )

    if not 0.50 <= parameters.target_atr_multiple <= 10.00:
        errors.append(
            "Target ATR이 허용 범위를 벗어났습니다."
        )

    if not 1 <= parameters.maximum_holding_days <= 90:
        errors.append(
            "Maximum Holding Days가 허용 범위를 "
            "벗어났습니다."
        )

    if not 0.0 < parameters.position_percent <= 25.0:
        errors.append(
            "Position Percent가 허용 범위를 "
            "벗어났습니다."
        )

    return (
        not errors,
        errors,
    )


def determine_provider_profile(
    runtime_mode: str,
) -> tuple[
    str,
    str,
]:
    """
    Runtime Mode를 Provider Profile로 변환합니다.
    """

    normalized_mode = (
        runtime_mode
        .strip()
        .upper()
    )

    mapping = {
        "LIVE_READY": (
            "LIVE",
            "실거래 Runtime 설정",
        ),
        "PAPER_READY": (
            "PAPER",
            "모의투자 Runtime 설정",
        ),
        "ANALYSIS_ONLY": (
            "ANALYSIS",
            "분석 및 백테스트 Runtime 설정",
        ),
        "RESEARCH_ONLY": (
            "RESEARCH",
            "연구 전용 Runtime 설정",
        ),
        "BLOCKED": (
            "NONE",
            "사용 불가능 Runtime 설정",
        ),
    }

    return mapping.get(
        normalized_mode,
        (
            "NONE",
            "사용 불가능 Runtime 설정",
        ),
    )


def determine_provider_status(
    runtime_mode: str,
    guard_status: str,
    all_checks_passed: bool,
) -> str:
    """
    Provider 상태를 결정합니다.
    """

    if not all_checks_passed:
        return "FAILED"

    if (
        runtime_mode == "BLOCKED"
        or guard_status in {
            "BLOCKED",
            "FAILED",
        }
    ):
        return "BLOCKED"

    if runtime_mode in {
        "ANALYSIS_ONLY",
        "RESEARCH_ONLY",
    }:
        return "LIMITED"

    return "READY"


def build_allowed_operations(
    analysis_enabled: bool,
    backtest_enabled: bool,
    research_enabled: bool,
    paper_execution_enabled: bool,
    live_execution_enabled: bool,
) -> tuple[
    list[str],
    list[str],
]:
    """
    허용된 작업과 차단된 작업 목록을 생성합니다.
    """

    operation_map = {
        "ANALYSIS": analysis_enabled,
        "BACKTEST": backtest_enabled,
        "RESEARCH": research_enabled,
        "PAPER_EXECUTION": (
            paper_execution_enabled
        ),
        "LIVE_EXECUTION": (
            live_execution_enabled
        ),
    }

    allowed_operations = [
        operation
        for operation, allowed
        in operation_map.items()
        if allowed
    ]

    blocked_operations = [
        operation
        for operation, allowed
        in operation_map.items()
        if not allowed
    ]

    return (
        allowed_operations,
        blocked_operations,
    )


def validate_permissions(
    runtime_mode: str,
    analysis_enabled: bool,
    backtest_enabled: bool,
    research_enabled: bool,
    paper_execution_enabled: bool,
    live_execution_enabled: bool,
) -> tuple[
    bool,
    list[str],
]:
    """
    Runtime Mode와 권한의 일관성을 검사합니다.
    """

    errors: list[str] = []

    if runtime_mode == "LIVE_READY":
        if not live_execution_enabled:
            errors.append(
                "LIVE_READY인데 실거래 권한이 없습니다."
            )

    elif runtime_mode == "PAPER_READY":
        if not paper_execution_enabled:
            errors.append(
                "PAPER_READY인데 모의투자 권한이 없습니다."
            )

        if live_execution_enabled:
            errors.append(
                "PAPER_READY에서 실거래 권한이 "
                "활성화되었습니다."
            )

    elif runtime_mode in {
        "ANALYSIS_ONLY",
        "RESEARCH_ONLY",
    }:
        if paper_execution_enabled:
            errors.append(
                f"{runtime_mode}에서 모의투자 권한이 "
                "활성화되었습니다."
            )

        if live_execution_enabled:
            errors.append(
                f"{runtime_mode}에서 실거래 권한이 "
                "활성화되었습니다."
            )

    elif runtime_mode == "BLOCKED":
        if any(
            [
                analysis_enabled,
                backtest_enabled,
                research_enabled,
                paper_execution_enabled,
                live_execution_enabled,
            ]
        ):
            errors.append(
                "BLOCKED 상태인데 허용된 작업이 있습니다."
            )

    if runtime_mode != "BLOCKED":
        if not analysis_enabled:
            errors.append(
                "사용 가능한 Runtime인데 분석 권한이 없습니다."
            )

        if not backtest_enabled:
            errors.append(
                "사용 가능한 Runtime인데 백테스트 권한이 없습니다."
            )

        if not research_enabled:
            errors.append(
                "사용 가능한 Runtime인데 연구 권한이 없습니다."
            )

    return (
        not errors,
        errors,
    )


def build_provider_notes(
    provider_status: str,
    provider_profile: str,
    runtime_mode: str,
    parameter_errors: list[str],
    permission_errors: list[str],
    manual_approval_required: bool,
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    Provider 결과 설명을 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if provider_status == "READY":
        reasons.append(
            "V8.8 Runtime Guard 검사를 통과한 "
            "전략 설정을 불러왔습니다."
        )

    elif provider_status == "LIMITED":
        reasons.append(
            "전략 설정은 준비되었지만 실행 권한이 "
            "제한된 상태입니다."
        )

    elif provider_status == "BLOCKED":
        reasons.append(
            "Runtime Guard 상태에 따라 전략 사용이 "
            "차단되었습니다."
        )

    else:
        reasons.append(
            "Runtime Configuration 생성 중 "
            "검사 오류가 확인되었습니다."
        )

    if provider_profile == "LIVE":
        next_actions.extend(
            [
                "실거래 모듈 연결 전에 계좌 상태를 확인합니다.",
                "최종 주문 수량과 손실 제한을 확인합니다.",
                "사용자 승인 후에만 주문 모듈에 전달합니다.",
            ]
        )

    elif provider_profile == "PAPER":
        next_actions.extend(
            [
                "모의투자 계좌에만 설정을 전달합니다.",
                "실제 주문 모듈과 완전히 분리합니다.",
                "모의 체결 및 포지션 로그를 저장합니다.",
            ]
        )

    elif provider_profile == "ANALYSIS":
        next_actions.extend(
            [
                "분석기와 백테스터에서만 설정을 사용합니다.",
                "실제 주문과 모의 주문 모듈에는 전달하지 않습니다.",
                "Registry 상태가 바뀌면 V8.7부터 다시 실행합니다.",
            ]
        )

    elif provider_profile == "RESEARCH":
        next_actions.extend(
            [
                "연구 및 검증 모듈에서만 사용합니다.",
                "추가 Walk-Forward 검증을 수행합니다.",
                "실행 엔진에는 전달하지 않습니다.",
            ]
        )

    else:
        next_actions.extend(
            [
                "V8.7 Configuration 파일을 확인합니다.",
                "V8.8 Runtime Guard를 다시 실행합니다.",
                "Runtime Guard의 Blocking Reasons를 확인합니다.",
            ]
        )

    for error in parameter_errors:
        warnings.append(
            f"Parameter error: {error}"
        )

    for error in permission_errors:
        warnings.append(
            f"Permission error: {error}"
        )

    if manual_approval_required:
        warnings.append(
            "실행 관련 모든 단계에는 수동 승인이 필요합니다."
        )

    if runtime_mode == "ANALYSIS_ONLY":
        warnings.append(
            "현재 설정에서는 실거래와 모의투자가 "
            "모두 차단됩니다."
        )

    warnings.append(
        "이 Provider는 Runtime 설정만 제공하며 "
        "실제 주문을 생성하거나 전송하지 않습니다."
    )

    return (
        reasons,
        warnings,
        next_actions,
    )


def run_strategy_runtime_provider(
    symbol: str = "AAPL",
    source_file: str | Path | None = None,
) -> StrategyRuntimeConfiguration:
    """
    V8.8 Runtime Guard를 읽고
    최종 Runtime Configuration을 생성합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if source_file is None:
        runtime_guard_path = (
            find_latest_runtime_guard_file(
                normalized_symbol
            )
        )
    else:
        runtime_guard_path = Path(
            source_file
        )

    payload = load_json_file(
        runtime_guard_path
    )

    validate_runtime_guard_payload(
        payload
    )

    source_symbol = normalize_symbol(
        str(
            payload.get(
                "symbol",
                "",
            )
        )
    )

    if source_symbol != normalized_symbol:
        raise ValueError(
            "요청한 Symbol과 Runtime Guard Symbol이 "
            "일치하지 않습니다."
        )

    runtime_mode = str(
        payload.get(
            "runtime_mode",
            "BLOCKED",
        )
    ).upper()

    guard_status = str(
        payload.get(
            "guard_status",
            "FAILED",
        )
    ).upper()

    entry_score = safe_float(
        payload.get(
            "entry_score"
        )
    )

    exit_score = safe_float(
        payload.get(
            "exit_score"
        )
    )

    stop_atr_multiple = safe_float(
        payload.get(
            "stop_atr_multiple"
        )
    )

    target_atr_multiple = safe_float(
        payload.get(
            "target_atr_multiple"
        )
    )

    maximum_holding_days = safe_int(
        payload.get(
            "maximum_holding_days"
        )
    )

    position_percent = safe_float(
        payload.get(
            "position_percent"
        )
    )

    missing_parameters: list[str] = []

    if entry_score is None:
        missing_parameters.append(
            "entry_score"
        )

    if exit_score is None:
        missing_parameters.append(
            "exit_score"
        )

    if stop_atr_multiple is None:
        missing_parameters.append(
            "stop_atr_multiple"
        )

    if target_atr_multiple is None:
        missing_parameters.append(
            "target_atr_multiple"
        )

    if maximum_holding_days is None:
        missing_parameters.append(
            "maximum_holding_days"
        )

    if position_percent is None:
        missing_parameters.append(
            "position_percent"
        )

    if missing_parameters:
        raise ValueError(
            "Runtime Guard에 필수 파라미터가 없습니다: "
            + ", ".join(
                missing_parameters
            )
        )

    parameters = RuntimeStrategyParameters(
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
    )

    (
        parameter_checks_passed,
        parameter_errors,
    ) = validate_strategy_parameters(
        parameters
    )

    analysis_enabled = safe_bool(
        payload.get(
            "analysis_allowed"
        )
    )

    backtest_enabled = safe_bool(
        payload.get(
            "backtest_allowed"
        )
    )

    research_enabled = safe_bool(
        payload.get(
            "research_allowed"
        )
    )

    paper_execution_enabled = safe_bool(
        payload.get(
            "paper_execution_allowed"
        )
    )

    live_execution_enabled = safe_bool(
        payload.get(
            "live_execution_allowed"
        )
    )

    (
        permission_checks_passed,
        permission_errors,
    ) = validate_permissions(
        runtime_mode=runtime_mode,
        analysis_enabled=analysis_enabled,
        backtest_enabled=backtest_enabled,
        research_enabled=research_enabled,
        paper_execution_enabled=(
            paper_execution_enabled
        ),
        live_execution_enabled=(
            live_execution_enabled
        ),
    )

    source_checks_passed = (
        runtime_guard_path.exists()
        and source_symbol
        == normalized_symbol
        and runtime_mode
        in VALID_RUNTIME_MODES
        and guard_status
        in VALID_GUARD_STATUSES
    )

    guard_all_checks_passed = safe_bool(
        payload.get(
            "all_checks_passed"
        )
    )

    all_checks_passed = (
        source_checks_passed
        and parameter_checks_passed
        and permission_checks_passed
        and guard_all_checks_passed
    )

    (
        provider_profile,
        provider_label,
    ) = determine_provider_profile(
        runtime_mode
    )

    provider_status = determine_provider_status(
        runtime_mode=runtime_mode,
        guard_status=guard_status,
        all_checks_passed=all_checks_passed,
    )

    provider_ready = (
        provider_status
        in {
            "READY",
            "LIMITED",
        }
        and provider_profile
        != "NONE"
    )

    (
        allowed_operations,
        blocked_operations,
    ) = build_allowed_operations(
        analysis_enabled=analysis_enabled,
        backtest_enabled=backtest_enabled,
        research_enabled=research_enabled,
        paper_execution_enabled=(
            paper_execution_enabled
        ),
        live_execution_enabled=(
            live_execution_enabled
        ),
    )

    manual_approval_required = safe_bool(
        payload.get(
            "manual_approval_required"
        ),
        default=True,
    )

    (
        reasons,
        warnings,
        next_actions,
    ) = build_provider_notes(
        provider_status=provider_status,
        provider_profile=provider_profile,
        runtime_mode=runtime_mode,
        parameter_errors=parameter_errors,
        permission_errors=permission_errors,
        manual_approval_required=(
            manual_approval_required
        ),
    )

    result = StrategyRuntimeConfiguration(
        version="V8.9",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        source_runtime_guard_file=str(
            runtime_guard_path
        ),

        provider_status=provider_status,
        provider_profile=provider_profile,
        provider_label=provider_label,

        configuration_mode=str(
            payload.get(
                "configuration_mode",
                "UNAVAILABLE",
            )
        ).upper(),

        runtime_mode=runtime_mode,
        guard_status=guard_status,

        strategy_source=str(
            payload.get(
                "strategy_source",
                "NONE",
            )
        ),

        strategy_status=str(
            payload.get(
                "strategy_status",
                "UNREGISTERED",
            )
        ),

        strategy_name=(
            str(
                payload.get(
                    "strategy_name"
                )
            )
            if payload.get(
                "strategy_name"
            )
            is not None
            else None
        ),

        strategy_type=(
            str(
                payload.get(
                    "strategy_type"
                )
            )
            if payload.get(
                "strategy_type"
            )
            is not None
            else None
        ),

        parameters=parameters,

        analysis_enabled=analysis_enabled,
        backtest_enabled=backtest_enabled,
        research_enabled=research_enabled,
        paper_execution_enabled=(
            paper_execution_enabled
        ),
        live_execution_enabled=(
            live_execution_enabled
        ),

        live_execution_blocked=(
            not live_execution_enabled
        ),
        paper_execution_blocked=(
            not paper_execution_enabled
        ),

        manual_approval_required=(
            manual_approval_required
        ),
        provider_ready=provider_ready,
        source_checks_passed=(
            source_checks_passed
        ),
        permission_checks_passed=(
            permission_checks_passed
        ),
        parameter_checks_passed=(
            parameter_checks_passed
        ),
        all_checks_passed=(
            all_checks_passed
        ),

        allowed_operations=(
            allowed_operations
        ),
        blocked_operations=(
            blocked_operations
        ),

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_strategy_runtime_provider(
        result
    )

    return result


def save_strategy_runtime_provider(
    result: StrategyRuntimeConfiguration,
) -> tuple[
    Path,
    Path,
]:
    """
    Runtime Configuration을 JSON으로 저장합니다.
    """

    RUNTIME_PROVIDER_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        RUNTIME_PROVIDER_DIRECTORY
        / (
            f"{result.symbol}_"
            "strategy_runtime_provider_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        RUNTIME_PROVIDER_DIRECTORY
        / (
            f"{result.symbol}_"
            "strategy_runtime_provider_latest.json"
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


def get_runtime_parameters(
    configuration: StrategyRuntimeConfiguration,
) -> RuntimeStrategyParameters:
    """
    전략 파라미터를 반환합니다.
    """

    if not configuration.provider_ready:
        raise RuntimeError(
            "Runtime Provider가 준비되지 않았습니다."
        )

    return configuration.parameters


def require_operation(
    configuration: StrategyRuntimeConfiguration,
    operation: str,
) -> None:
    """
    특정 작업이 허용되는지 검사합니다.

    허용되지 않은 작업이면 RuntimeError를 발생시킵니다.
    """

    normalized_operation = (
        operation
        .strip()
        .upper()
    )

    valid_operations = {
        "ANALYSIS",
        "BACKTEST",
        "RESEARCH",
        "PAPER_EXECUTION",
        "LIVE_EXECUTION",
    }

    if normalized_operation not in valid_operations:
        raise ValueError(
            "알 수 없는 Runtime Operation입니다: "
            f"{normalized_operation}"
        )

    if (
        normalized_operation
        not in configuration.allowed_operations
    ):
        raise RuntimeError(
            f"{normalized_operation} 작업은 현재 "
            f"Runtime Mode {configuration.runtime_mode}에서 "
            "허용되지 않습니다."
        )


def is_operation_allowed(
    configuration: StrategyRuntimeConfiguration,
    operation: str,
) -> bool:
    """
    특정 작업의 허용 여부를 bool로 반환합니다.
    """

    normalized_operation = (
        operation
        .strip()
        .upper()
    )

    return (
        normalized_operation
        in configuration.allowed_operations
    )


def print_strategy_runtime_provider(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    V8.9 Runtime Provider 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V8.9 "
        "STRATEGY RUNTIME CONFIGURATION PROVIDER"
    )
    print("=" * 140)

    print(
        f"Provider status                : "
        f"{result.provider_status}"
    )

    print(
        f"Provider profile               : "
        f"{result.provider_profile}"
    )

    print(
        f"Provider label                 : "
        f"{result.provider_label}"
    )

    print(
        f"Provider ready                 : "
        f"{result.provider_ready}"
    )

    print(
        f"Configuration mode             : "
        f"{result.configuration_mode}"
    )

    print(
        f"Runtime mode                   : "
        f"{result.runtime_mode}"
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
        f"{result.parameters.entry_score:.2f}"
    )

    print(
        f"Exit score                     : "
        f"{result.parameters.exit_score:.2f}"
    )

    print(
        f"Stop ATR                       : "
        f"{result.parameters.stop_atr_multiple:.2f}"
    )

    print(
        f"Target ATR                     : "
        f"{result.parameters.target_atr_multiple:.2f}"
    )

    print(
        f"Maximum holding days           : "
        f"{result.parameters.maximum_holding_days}"
    )

    print(
        f"Position percent               : "
        f"{result.parameters.position_percent:.2f}%"
    )

    print()
    print("RUNTIME PERMISSIONS")
    print("-" * 140)

    print(
        f"Analysis enabled               : "
        f"{result.analysis_enabled}"
    )

    print(
        f"Backtest enabled               : "
        f"{result.backtest_enabled}"
    )

    print(
        f"Research enabled               : "
        f"{result.research_enabled}"
    )

    print(
        f"Paper execution enabled        : "
        f"{result.paper_execution_enabled}"
    )

    print(
        f"Live execution enabled         : "
        f"{result.live_execution_enabled}"
    )

    print(
        f"Paper execution blocked        : "
        f"{result.paper_execution_blocked}"
    )

    print(
        f"Live execution blocked         : "
        f"{result.live_execution_blocked}"
    )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Source checks passed           : "
        f"{result.source_checks_passed}"
    )

    print(
        f"Permission checks passed       : "
        f"{result.permission_checks_passed}"
    )

    print(
        f"Parameter checks passed        : "
        f"{result.parameter_checks_passed}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print(
        f"Manual approval required       : "
        f"{result.manual_approval_required}"
    )

    print()
    print("ALLOWED OPERATIONS")
    print("-" * 140)

    if result.allowed_operations:
        for operation in result.allowed_operations:
            print(
                f"- {operation}"
            )
    else:
        print(
            "- None"
        )

    print()
    print("BLOCKED OPERATIONS")
    print("-" * 140)

    if result.blocked_operations:
        for operation in result.blocked_operations:
            print(
                f"- {operation}"
            )
    else:
        print(
            "- None"
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
        f"Source Runtime Guard file      : "
        f"{result.source_runtime_guard_file}"
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
        "주의: 이 Provider는 Runtime 설정과 권한만 제공하며 "
        "실제 주문이나 자동 매매를 실행하지 않습니다."
    )