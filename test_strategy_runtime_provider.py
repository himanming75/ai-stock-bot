import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

from backtest.strategy_runtime_provider import (
    VALID_GUARD_STATUSES,
    VALID_PROVIDER_PROFILES,
    VALID_PROVIDER_STATUSES,
    VALID_RUNTIME_MODES,
    RuntimeStrategyParameters,
    StrategyRuntimeConfiguration,
    build_allowed_operations,
    determine_provider_profile,
    determine_provider_status,
    get_runtime_parameters,
    is_operation_allowed,
    print_strategy_runtime_provider,
    require_operation,
    run_strategy_runtime_provider,
    save_strategy_runtime_provider,
    validate_permissions,
    validate_strategy_parameters,
)


VALID_CONFIGURATION_MODES = {
    "ACTIVE",
    "PAPER_TRADING",
    "BASELINE",
    "RESEARCH_ONLY",
    "UNAVAILABLE",
}


VALID_STRATEGY_SOURCES = {
    "ACTIVE_STRATEGY",
    "PAPER_STRATEGY",
    "PROMOTION_BASELINE",
    "BASELINE_DEFAULT",
    "RESEARCH_ARCHIVE",
    "NONE",
}


VALID_STRATEGY_STATUSES = {
    "ACTIVE",
    "PAPER_TRADING",
    "BASELINE_RETAINED",
    "BASELINE",
    "RESEARCH_ONLY",
    "UNREGISTERED",
}


VALID_OPERATIONS = {
    "ANALYSIS",
    "BACKTEST",
    "RESEARCH",
    "PAPER_EXECUTION",
    "LIVE_EXECUTION",
}


def print_test_header() -> None:
    """
    V8.9 Strategy Runtime Provider
    테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V8.9 "
        "STRATEGY RUNTIME CONFIGURATION PROVIDER TEST"
    )
    print("=" * 140)


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
        raise RuntimeError(
            "JSON 최상위 데이터가 "
            "Dictionary 형식이 아닙니다."
        )

    return payload


def calculate_expected_provider_profile(
    runtime_mode: str,
) -> tuple[str, str]:
    """
    Runtime Mode에서 예상되는
    Provider Profile과 Label을 독립적으로 계산합니다.
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


def calculate_expected_provider_status(
    runtime_mode: str,
    guard_status: str,
    all_checks_passed: bool,
) -> str:
    """
    Runtime Mode와 Guard 상태를 이용하여
    예상 Provider Status를 계산합니다.
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


def calculate_expected_operations(
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
    권한 상태에서 예상되는 허용·차단 작업을
    독립적으로 계산합니다.
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

    allowed = [
        operation
        for operation, enabled
        in operation_map.items()
        if enabled
    ]

    blocked = [
        operation
        for operation, enabled
        in operation_map.items()
        if not enabled
    ]

    return (
        allowed,
        blocked,
    )


def calculate_expected_provider_ready(
    provider_status: str,
    provider_profile: str,
) -> bool:
    """
    Provider Status와 Profile에서
    예상 Provider Ready 값을 계산합니다.
    """

    return (
        provider_status
        in {
            "READY",
            "LIMITED",
        }
        and provider_profile
        != "NONE"
    )


def validate_parameter_structure(
    parameters: RuntimeStrategyParameters,
) -> None:
    """
    RuntimeStrategyParameters의 구조와
    자료형을 검사합니다.
    """

    if not isinstance(
        parameters,
        RuntimeStrategyParameters,
    ):
        raise RuntimeError(
            "parameters가 RuntimeStrategyParameters "
            "형식이 아닙니다."
        )

    float_fields = {
        "Entry Score": (
            parameters.entry_score
        ),
        "Exit Score": (
            parameters.exit_score
        ),
        "Stop ATR": (
            parameters.stop_atr_multiple
        ),
        "Target ATR": (
            parameters.target_atr_multiple
        ),
        "Position Percent": (
            parameters.position_percent
        ),
    }

    for field_name, value in (
        float_fields.items()
    ):
        if not isinstance(
            value,
            float,
        ):
            raise RuntimeError(
                f"{field_name}가 float 형식이 아닙니다."
            )

    if not isinstance(
        parameters.maximum_holding_days,
        int,
    ):
        raise RuntimeError(
            "Maximum Holding Days가 int 형식이 아닙니다."
        )

    parameter_payload = parameters.to_dict()

    required_keys = {
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
    }

    if set(parameter_payload.keys()) != required_keys:
        raise RuntimeError(
            "RuntimeStrategyParameters.to_dict()의 "
            "키가 예상 구조와 일치하지 않습니다."
        )


def validate_parameters_are_immutable(
    parameters: RuntimeStrategyParameters,
) -> None:
    """
    RuntimeStrategyParameters가 frozen=True로
    생성되어 값을 직접 변경할 수 없는지 검사합니다.
    """

    original_entry_score = (
        parameters.entry_score
    )

    immutable = False

    try:
        parameters.entry_score = 99.0

    except (
        FrozenInstanceError,
        AttributeError,
    ):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "RuntimeStrategyParameters의 값을 "
            "직접 변경할 수 있습니다."
        )

    if (
        parameters.entry_score
        != original_entry_score
    ):
        raise RuntimeError(
            "불변 파라미터의 Entry Score가 "
            "변경되었습니다."
        )


def validate_result_structure(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    V8.9 Runtime Provider 결과의
    기본 구조와 자료형을 검사합니다.
    """

    if result.version != "V8.9":
        raise RuntimeError(
            "Runtime Provider 버전이 V8.9가 아닙니다: "
            f"{result.version}"
        )

    if not result.symbol:
        raise RuntimeError(
            "Symbol이 비어 있습니다."
        )

    if result.symbol != result.symbol.upper():
        raise RuntimeError(
            "Symbol이 대문자로 정규화되지 않았습니다."
        )

    if not result.created_at:
        raise RuntimeError(
            "Created At이 비어 있습니다."
        )

    if not result.source_runtime_guard_file:
        raise RuntimeError(
            "Source Runtime Guard File이 비어 있습니다."
        )

    if (
        result.provider_status
        not in VALID_PROVIDER_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Provider Status입니다: "
            f"{result.provider_status}"
        )

    if (
        result.provider_profile
        not in VALID_PROVIDER_PROFILES
    ):
        raise RuntimeError(
            "올바르지 않은 Provider Profile입니다: "
            f"{result.provider_profile}"
        )

    if not result.provider_label:
        raise RuntimeError(
            "Provider Label이 비어 있습니다."
        )

    if (
        result.runtime_mode
        not in VALID_RUNTIME_MODES
    ):
        raise RuntimeError(
            "올바르지 않은 Runtime Mode입니다: "
            f"{result.runtime_mode}"
        )

    if (
        result.guard_status
        not in VALID_GUARD_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Guard Status입니다: "
            f"{result.guard_status}"
        )

    if (
        result.configuration_mode
        not in VALID_CONFIGURATION_MODES
    ):
        raise RuntimeError(
            "올바르지 않은 Configuration Mode입니다: "
            f"{result.configuration_mode}"
        )

    if (
        result.strategy_source
        not in VALID_STRATEGY_SOURCES
    ):
        raise RuntimeError(
            "올바르지 않은 Strategy Source입니다: "
            f"{result.strategy_source}"
        )

    if (
        result.strategy_status
        not in VALID_STRATEGY_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Strategy Status입니다: "
            f"{result.strategy_status}"
        )

    validate_parameter_structure(
        result.parameters
    )

    boolean_fields = {
        "Analysis Enabled": (
            result.analysis_enabled
        ),
        "Backtest Enabled": (
            result.backtest_enabled
        ),
        "Research Enabled": (
            result.research_enabled
        ),
        "Paper Execution Enabled": (
            result.paper_execution_enabled
        ),
        "Live Execution Enabled": (
            result.live_execution_enabled
        ),
        "Live Execution Blocked": (
            result.live_execution_blocked
        ),
        "Paper Execution Blocked": (
            result.paper_execution_blocked
        ),
        "Manual Approval Required": (
            result.manual_approval_required
        ),
        "Provider Ready": (
            result.provider_ready
        ),
        "Source Checks Passed": (
            result.source_checks_passed
        ),
        "Permission Checks Passed": (
            result.permission_checks_passed
        ),
        "Parameter Checks Passed": (
            result.parameter_checks_passed
        ),
        "All Checks Passed": (
            result.all_checks_passed
        ),
    }

    for field_name, value in (
        boolean_fields.items()
    ):
        if not isinstance(
            value,
            bool,
        ):
            raise RuntimeError(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    list_fields = {
        "Allowed Operations": (
            result.allowed_operations
        ),
        "Blocked Operations": (
            result.blocked_operations
        ),
        "Reasons": result.reasons,
        "Warnings": result.warnings,
        "Next Actions": result.next_actions,
    }

    for field_name, value in (
        list_fields.items()
    ):
        if not isinstance(
            value,
            list,
        ):
            raise RuntimeError(
                f"{field_name}가 List 형식이 아닙니다."
            )

    if not result.reasons:
        raise RuntimeError(
            "Reasons가 비어 있습니다."
        )

    if not result.warnings:
        raise RuntimeError(
            "Warnings가 비어 있습니다."
        )

    if not result.next_actions:
        raise RuntimeError(
            "Next Actions가 비어 있습니다."
        )

    unknown_allowed_operations = (
        set(result.allowed_operations)
        - VALID_OPERATIONS
    )

    if unknown_allowed_operations:
        raise RuntimeError(
            "Allowed Operations에 알 수 없는 작업이 "
            "포함되어 있습니다: "
            f"{sorted(unknown_allowed_operations)}"
        )

    unknown_blocked_operations = (
        set(result.blocked_operations)
        - VALID_OPERATIONS
    )

    if unknown_blocked_operations:
        raise RuntimeError(
            "Blocked Operations에 알 수 없는 작업이 "
            "포함되어 있습니다: "
            f"{sorted(unknown_blocked_operations)}"
        )


def validate_source_runtime_guard(
    result: StrategyRuntimeConfiguration,
) -> dict[str, Any]:
    """
    V8.8 Runtime Guard 원본 파일과
    V8.9 Provider 결과를 비교합니다.
    """

    source_path = Path(
        result.source_runtime_guard_file
    )

    if not source_path.exists():
        raise RuntimeError(
            "Source Runtime Guard 파일이 "
            "존재하지 않습니다: "
            f"{source_path}"
        )

    if source_path.stat().st_size <= 0:
        raise RuntimeError(
            "Source Runtime Guard 파일이 비어 있습니다."
        )

    source_payload = load_json_file(
        source_path
    )

    source_version = str(
        source_payload.get(
            "version",
            "",
        )
    ).upper()

    if source_version != "V8.8":
        raise RuntimeError(
            "Source Runtime Guard 파일의 "
            "버전이 V8.8이 아닙니다."
        )

    source_symbol = str(
        source_payload.get(
            "symbol",
            "",
        )
    ).upper()

    if source_symbol != result.symbol:
        raise RuntimeError(
            "Source Runtime Guard Symbol과 "
            "Provider Symbol이 일치하지 않습니다."
        )

    source_runtime_mode = str(
        source_payload.get(
            "runtime_mode",
            "",
        )
    ).upper()

    if (
        source_runtime_mode
        != result.runtime_mode
    ):
        raise RuntimeError(
            "Source Runtime Mode와 Provider Runtime Mode가 "
            "일치하지 않습니다."
        )

    source_guard_status = str(
        source_payload.get(
            "guard_status",
            "",
        )
    ).upper()

    if (
        source_guard_status
        != result.guard_status
    ):
        raise RuntimeError(
            "Source Guard Status와 Provider Guard Status가 "
            "일치하지 않습니다."
        )

    source_configuration_mode = str(
        source_payload.get(
            "configuration_mode",
            "",
        )
    ).upper()

    if (
        source_configuration_mode
        != result.configuration_mode
    ):
        raise RuntimeError(
            "Source Configuration Mode와 Provider의 "
            "Configuration Mode가 일치하지 않습니다."
        )

    source_strategy_source = str(
        source_payload.get(
            "strategy_source",
            "NONE",
        )
    )

    if (
        source_strategy_source
        != result.strategy_source
    ):
        raise RuntimeError(
            "Strategy Source가 Source Runtime Guard와 "
            "일치하지 않습니다."
        )

    source_strategy_status = str(
        source_payload.get(
            "strategy_status",
            "UNREGISTERED",
        )
    )

    if (
        source_strategy_status
        != result.strategy_status
    ):
        raise RuntimeError(
            "Strategy Status가 Source Runtime Guard와 "
            "일치하지 않습니다."
        )

    return source_payload


def validate_source_parameter_matches(
    result: StrategyRuntimeConfiguration,
    source_payload: dict[str, Any],
) -> None:
    """
    Provider 파라미터가 V8.8 Runtime Guard와
    일치하는지 검사합니다.
    """

    parameter_checks = {
        "entry_score": (
            result.parameters.entry_score,
            safe_float(
                source_payload.get(
                    "entry_score"
                )
            ),
        ),
        "exit_score": (
            result.parameters.exit_score,
            safe_float(
                source_payload.get(
                    "exit_score"
                )
            ),
        ),
        "stop_atr_multiple": (
            result.parameters.stop_atr_multiple,
            safe_float(
                source_payload.get(
                    "stop_atr_multiple"
                )
            ),
        ),
        "target_atr_multiple": (
            result.parameters.target_atr_multiple,
            safe_float(
                source_payload.get(
                    "target_atr_multiple"
                )
            ),
        ),
        "maximum_holding_days": (
            float(
                result.parameters.maximum_holding_days
            ),
            safe_float(
                source_payload.get(
                    "maximum_holding_days"
                )
            ),
        ),
        "position_percent": (
            result.parameters.position_percent,
            safe_float(
                source_payload.get(
                    "position_percent"
                )
            ),
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in parameter_checks.items():
        if expected_value is None:
            raise RuntimeError(
                f"Source Runtime Guard의 {field_name} 값을 "
                "숫자로 변환할 수 없습니다."
            )

        if abs(
            float(actual_value)
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"{field_name} 값이 Source Runtime Guard와 "
                "일치하지 않습니다. "
                f"Expected={expected_value}, "
                f"Actual={actual_value}"
            )


def validate_source_permission_matches(
    result: StrategyRuntimeConfiguration,
    source_payload: dict[str, Any],
) -> None:
    """
    Provider 권한이 V8.8 Runtime Guard 권한과
    일치하는지 검사합니다.
    """

    permission_checks = {
        "analysis_allowed": (
            result.analysis_enabled
        ),
        "backtest_allowed": (
            result.backtest_enabled
        ),
        "research_allowed": (
            result.research_enabled
        ),
        "paper_execution_allowed": (
            result.paper_execution_enabled
        ),
        "live_execution_allowed": (
            result.live_execution_enabled
        ),
    }

    for source_field, actual_value in (
        permission_checks.items()
    ):
        expected_value = source_payload.get(
            source_field
        )

        if not isinstance(
            expected_value,
            bool,
        ):
            raise RuntimeError(
                f"Source Runtime Guard의 {source_field}가 "
                "bool 형식이 아닙니다."
            )

        if expected_value != actual_value:
            raise RuntimeError(
                f"{source_field} 권한이 Source Runtime Guard와 "
                "일치하지 않습니다."
            )

    expected_manual_approval = source_payload.get(
        "manual_approval_required"
    )

    if not isinstance(
        expected_manual_approval,
        bool,
    ):
        raise RuntimeError(
            "Source Runtime Guard의 "
            "manual_approval_required가 bool 형식이 아닙니다."
        )

    if (
        expected_manual_approval
        != result.manual_approval_required
    ):
        raise RuntimeError(
            "Manual Approval Required가 "
            "Source Runtime Guard와 일치하지 않습니다."
        )


def validate_provider_profile(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    Runtime Mode가 Provider Profile로
    정상 변환되었는지 검사합니다.
    """

    (
        expected_profile,
        expected_label,
    ) = calculate_expected_provider_profile(
        result.runtime_mode
    )

    module_result = determine_provider_profile(
        result.runtime_mode
    )

    if module_result != (
        expected_profile,
        expected_label,
    ):
        raise RuntimeError(
            "determine_provider_profile 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.provider_profile != expected_profile:
        raise RuntimeError(
            "Provider Profile이 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_profile}, "
            f"Actual={result.provider_profile}"
        )

    if result.provider_label != expected_label:
        raise RuntimeError(
            "Provider Label이 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_label}, "
            f"Actual={result.provider_label}"
        )


def validate_provider_status_result(
    result: StrategyRuntimeConfiguration,
    source_payload: dict[str, Any],
) -> None:
    """
    Provider Status와 Ready 상태의
    내부 일관성을 검사합니다.
    """

    source_all_checks_passed = (
        source_payload.get(
            "all_checks_passed"
        )
    )

    if not isinstance(
        source_all_checks_passed,
        bool,
    ):
        raise RuntimeError(
            "Source Runtime Guard의 all_checks_passed가 "
            "bool 형식이 아닙니다."
        )

    expected_all_checks = (
        result.source_checks_passed
        and result.permission_checks_passed
        and result.parameter_checks_passed
        and source_all_checks_passed
    )

    if (
        result.all_checks_passed
        != expected_all_checks
    ):
        raise RuntimeError(
            "Provider All Checks Passed 값이 개별 검사 및 "
            "V8.8 Guard 검사 결과와 일치하지 않습니다."
        )

    expected_status = (
        calculate_expected_provider_status(
            runtime_mode=result.runtime_mode,
            guard_status=result.guard_status,
            all_checks_passed=(
                result.all_checks_passed
            ),
        )
    )

    module_status = determine_provider_status(
        runtime_mode=result.runtime_mode,
        guard_status=result.guard_status,
        all_checks_passed=(
            result.all_checks_passed
        ),
    )

    if module_status != expected_status:
        raise RuntimeError(
            "determine_provider_status 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.provider_status != expected_status:
        raise RuntimeError(
            "Provider Status가 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_status}, "
            f"Actual={result.provider_status}"
        )

    expected_ready = (
        calculate_expected_provider_ready(
            provider_status=(
                result.provider_status
            ),
            provider_profile=(
                result.provider_profile
            ),
        )
    )

    if result.provider_ready != expected_ready:
        raise RuntimeError(
            "Provider Ready가 Provider Status 및 "
            "Profile과 일치하지 않습니다."
        )


def validate_parameter_checks(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    전략 파라미터 검사 결과를 확인합니다.
    """

    (
        expected_passed,
        expected_errors,
    ) = validate_strategy_parameters(
        result.parameters
    )

    if (
        result.parameter_checks_passed
        != expected_passed
    ):
        raise RuntimeError(
            "Parameter Checks Passed가 실제 "
            "파라미터 검사 결과와 일치하지 않습니다."
        )

    if expected_errors:
        for error_message in expected_errors:
            warning_found = any(
                error_message
                in str(warning)
                for warning in result.warnings
            )

            if not warning_found:
                raise RuntimeError(
                    "파라미터 오류가 Warnings에 "
                    "포함되지 않았습니다: "
                    f"{error_message}"
                )

    if result.parameters.entry_score <= (
        result.parameters.exit_score
    ):
        raise RuntimeError(
            "Entry Score는 Exit Score보다 "
            "높아야 합니다."
        )

    if not (
        0.50
        <= result.parameters.stop_atr_multiple
        <= 5.00
    ):
        raise RuntimeError(
            "Stop ATR이 허용 범위를 벗어났습니다."
        )

    if not (
        0.50
        <= result.parameters.target_atr_multiple
        <= 10.00
    ):
        raise RuntimeError(
            "Target ATR이 허용 범위를 벗어났습니다."
        )

    if not (
        1
        <= result.parameters.maximum_holding_days
        <= 90
    ):
        raise RuntimeError(
            "Maximum Holding Days가 허용 범위를 "
            "벗어났습니다."
        )

    if not (
        0.0
        < result.parameters.position_percent
        <= 25.0
    ):
        raise RuntimeError(
            "Position Percent가 허용 범위를 "
            "벗어났습니다."
        )


def validate_permission_checks(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    Runtime Mode와 Provider 권한의
    일관성을 검사합니다.
    """

    (
        expected_passed,
        expected_errors,
    ) = validate_permissions(
        runtime_mode=result.runtime_mode,
        analysis_enabled=(
            result.analysis_enabled
        ),
        backtest_enabled=(
            result.backtest_enabled
        ),
        research_enabled=(
            result.research_enabled
        ),
        paper_execution_enabled=(
            result.paper_execution_enabled
        ),
        live_execution_enabled=(
            result.live_execution_enabled
        ),
    )

    if (
        result.permission_checks_passed
        != expected_passed
    ):
        raise RuntimeError(
            "Permission Checks Passed가 실제 권한 "
            "검사 결과와 일치하지 않습니다."
        )

    if expected_errors:
        for error_message in expected_errors:
            warning_found = any(
                error_message
                in str(warning)
                for warning in result.warnings
            )

            if not warning_found:
                raise RuntimeError(
                    "권한 오류가 Warnings에 포함되지 "
                    "않았습니다: "
                    f"{error_message}"
                )

    if (
        result.live_execution_blocked
        != (
            not result.live_execution_enabled
        )
    ):
        raise RuntimeError(
            "Live Execution Blocked 값이 "
            "Live Execution Enabled와 일치하지 않습니다."
        )

    if (
        result.paper_execution_blocked
        != (
            not result.paper_execution_enabled
        )
    ):
        raise RuntimeError(
            "Paper Execution Blocked 값이 "
            "Paper Execution Enabled와 일치하지 않습니다."
        )


def validate_operation_lists(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    Allowed Operations와 Blocked Operations를
    검사합니다.
    """

    (
        expected_allowed,
        expected_blocked,
    ) = calculate_expected_operations(
        analysis_enabled=(
            result.analysis_enabled
        ),
        backtest_enabled=(
            result.backtest_enabled
        ),
        research_enabled=(
            result.research_enabled
        ),
        paper_execution_enabled=(
            result.paper_execution_enabled
        ),
        live_execution_enabled=(
            result.live_execution_enabled
        ),
    )

    module_allowed, module_blocked = (
        build_allowed_operations(
            analysis_enabled=(
                result.analysis_enabled
            ),
            backtest_enabled=(
                result.backtest_enabled
            ),
            research_enabled=(
                result.research_enabled
            ),
            paper_execution_enabled=(
                result.paper_execution_enabled
            ),
            live_execution_enabled=(
                result.live_execution_enabled
            ),
        )
    )

    if (
        module_allowed != expected_allowed
        or module_blocked != expected_blocked
    ):
        raise RuntimeError(
            "build_allowed_operations 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.allowed_operations != expected_allowed:
        raise RuntimeError(
            "Allowed Operations가 예상 결과와 "
            "일치하지 않습니다."
        )

    if result.blocked_operations != expected_blocked:
        raise RuntimeError(
            "Blocked Operations가 예상 결과와 "
            "일치하지 않습니다."
        )

    allowed_set = set(
        result.allowed_operations
    )

    blocked_set = set(
        result.blocked_operations
    )

    if allowed_set & blocked_set:
        raise RuntimeError(
            "동일한 작업이 Allowed와 Blocked에 "
            "동시에 포함되어 있습니다."
        )

    if (
        allowed_set | blocked_set
        != VALID_OPERATIONS
    ):
        raise RuntimeError(
            "Allowed와 Blocked Operations를 합친 결과가 "
            "전체 작업 목록과 일치하지 않습니다."
        )


def validate_operation_helpers(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    is_operation_allowed 및 require_operation
    보조 함수를 검사합니다.
    """

    for operation in VALID_OPERATIONS:
        expected_allowed = (
            operation
            in result.allowed_operations
        )

        actual_allowed = is_operation_allowed(
            result,
            operation,
        )

        if actual_allowed != expected_allowed:
            raise RuntimeError(
                f"is_operation_allowed 결과가 "
                f"{operation}의 실제 권한과 "
                "일치하지 않습니다."
            )

        if expected_allowed:
            try:
                require_operation(
                    result,
                    operation,
                )

            except Exception as error:
                raise RuntimeError(
                    f"허용된 {operation} 작업에서 "
                    "require_operation이 오류를 "
                    "발생시켰습니다: "
                    f"{error}"
                ) from error

        else:
            blocked_correctly = False

            try:
                require_operation(
                    result,
                    operation,
                )

            except RuntimeError:
                blocked_correctly = True

            if not blocked_correctly:
                raise RuntimeError(
                    f"차단된 {operation} 작업을 "
                    "require_operation이 허용했습니다."
                )

    invalid_operation_blocked = False

    try:
        require_operation(
            result,
            "INVALID_OPERATION",
        )

    except ValueError:
        invalid_operation_blocked = True

    if not invalid_operation_blocked:
        raise RuntimeError(
            "알 수 없는 Operation을 "
            "require_operation이 차단하지 않았습니다."
        )


def validate_get_runtime_parameters(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    get_runtime_parameters 함수가 동일한
    파라미터 객체를 반환하는지 검사합니다.
    """

    if result.provider_ready:
        returned_parameters = (
            get_runtime_parameters(
                result
            )
        )

        if returned_parameters != result.parameters:
            raise RuntimeError(
                "get_runtime_parameters가 Provider의 "
                "파라미터와 다른 값을 반환했습니다."
            )

    else:
        error_raised = False

        try:
            get_runtime_parameters(
                result
            )

        except RuntimeError:
            error_raised = True

        if not error_raised:
            raise RuntimeError(
                "Provider Ready가 False인데 "
                "get_runtime_parameters가 값을 반환했습니다."
            )


def validate_current_analysis_result(
    result: StrategyRuntimeConfiguration,
) -> None:
    """
    현재 AAPL ANALYSIS_ONLY 상태에서
    예상되는 V8.9 결과를 검사합니다.
    """

    if result.runtime_mode != "ANALYSIS_ONLY":
        return

    if result.provider_status != "LIMITED":
        raise RuntimeError(
            "ANALYSIS_ONLY인데 Provider Status가 "
            "LIMITED가 아닙니다."
        )

    if result.provider_profile != "ANALYSIS":
        raise RuntimeError(
            "ANALYSIS_ONLY인데 Provider Profile이 "
            "ANALYSIS가 아닙니다."
        )

    if (
        result.provider_label
        != "분석 및 백테스트 Runtime 설정"
    ):
        raise RuntimeError(
            "ANALYSIS Provider Label이 올바르지 않습니다."
        )

    if not result.provider_ready:
        raise RuntimeError(
            "ANALYSIS_ONLY Provider가 준비되지 않았습니다."
        )

    if not result.analysis_enabled:
        raise RuntimeError(
            "ANALYSIS_ONLY에서 분석 권한이 없습니다."
        )

    if not result.backtest_enabled:
        raise RuntimeError(
            "ANALYSIS_ONLY에서 백테스트 권한이 없습니다."
        )

    if not result.research_enabled:
        raise RuntimeError(
            "ANALYSIS_ONLY에서 연구 권한이 없습니다."
        )

    if result.paper_execution_enabled:
        raise RuntimeError(
            "ANALYSIS_ONLY에서 모의투자 권한이 "
            "활성화되었습니다."
        )

    if result.live_execution_enabled:
        raise RuntimeError(
            "ANALYSIS_ONLY에서 실거래 권한이 "
            "활성화되었습니다."
        )

    expected_allowed = [
        "ANALYSIS",
        "BACKTEST",
        "RESEARCH",
    ]

    expected_blocked = [
        "PAPER_EXECUTION",
        "LIVE_EXECUTION",
    ]

    if (
        result.allowed_operations
        != expected_allowed
    ):
        raise RuntimeError(
            "ANALYSIS_ONLY의 Allowed Operations가 "
            "예상 결과와 일치하지 않습니다."
        )

    if (
        result.blocked_operations
        != expected_blocked
    ):
        raise RuntimeError(
            "ANALYSIS_ONLY의 Blocked Operations가 "
            "예상 결과와 일치하지 않습니다."
        )

    if not result.manual_approval_required:
        raise RuntimeError(
            "Manual Approval Required가 False입니다."
        )

    analysis_warning_exists = any(
        (
            "실거래"
            in str(warning)
        )
        or (
            "모의투자"
            in str(warning)
        )
        for warning in result.warnings
    )

    if not analysis_warning_exists:
        raise RuntimeError(
            "Warnings에 실행 차단 설명이 없습니다."
        )


def validate_saved_files(
    result: StrategyRuntimeConfiguration,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    저장된 V8.9 Runtime Provider JSON 파일을 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            "시간별 Runtime Provider 보고서가 없습니다: "
            f"{report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            "Runtime Provider Latest 파일이 없습니다: "
            f"{latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 Runtime Provider 보고서가 "
            "비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "Runtime Provider Latest 파일이 비어 있습니다."
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "시간별 Runtime Provider 보고서와 "
            "Latest 파일의 내용이 일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_runtime_guard_file",
        "provider_status",
        "provider_profile",
        "provider_label",
        "configuration_mode",
        "runtime_mode",
        "guard_status",
        "strategy_source",
        "strategy_status",
        "strategy_name",
        "strategy_type",
        "parameters",
        "analysis_enabled",
        "backtest_enabled",
        "research_enabled",
        "paper_execution_enabled",
        "live_execution_enabled",
        "live_execution_blocked",
        "paper_execution_blocked",
        "manual_approval_required",
        "provider_ready",
        "source_checks_passed",
        "permission_checks_passed",
        "parameter_checks_passed",
        "all_checks_passed",
        "allowed_operations",
        "blocked_operations",
        "reasons",
        "warnings",
        "next_actions",
        "report_path",
        "latest_path",
    }

    missing_keys = (
        required_keys
        - set(report_payload.keys())
    )

    if missing_keys:
        raise RuntimeError(
            "저장된 V8.9 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    text_checks = {
        "version": result.version,
        "symbol": result.symbol,
        "source_runtime_guard_file": (
            result.source_runtime_guard_file
        ),
        "provider_status": (
            result.provider_status
        ),
        "provider_profile": (
            result.provider_profile
        ),
        "provider_label": (
            result.provider_label
        ),
        "configuration_mode": (
            result.configuration_mode
        ),
        "runtime_mode": (
            result.runtime_mode
        ),
        "guard_status": (
            result.guard_status
        ),
        "strategy_source": (
            result.strategy_source
        ),
        "strategy_status": (
            result.strategy_status
        ),
    }

    for field_name, expected_value in (
        text_checks.items()
    ):
        actual_value = report_payload.get(
            field_name
        )

        if str(actual_value) != str(expected_value):
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    boolean_checks = {
        "analysis_enabled": (
            result.analysis_enabled
        ),
        "backtest_enabled": (
            result.backtest_enabled
        ),
        "research_enabled": (
            result.research_enabled
        ),
        "paper_execution_enabled": (
            result.paper_execution_enabled
        ),
        "live_execution_enabled": (
            result.live_execution_enabled
        ),
        "live_execution_blocked": (
            result.live_execution_blocked
        ),
        "paper_execution_blocked": (
            result.paper_execution_blocked
        ),
        "manual_approval_required": (
            result.manual_approval_required
        ),
        "provider_ready": (
            result.provider_ready
        ),
        "source_checks_passed": (
            result.source_checks_passed
        ),
        "permission_checks_passed": (
            result.permission_checks_passed
        ),
        "parameter_checks_passed": (
            result.parameter_checks_passed
        ),
        "all_checks_passed": (
            result.all_checks_passed
        ),
    }

    for field_name, expected_value in (
        boolean_checks.items()
    ):
        actual_value = report_payload.get(
            field_name
        )

        if actual_value is not expected_value:
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    saved_parameters = report_payload.get(
        "parameters"
    )

    if not isinstance(
        saved_parameters,
        dict,
    ):
        raise RuntimeError(
            "저장된 parameters가 Dictionary가 아닙니다."
        )

    parameter_checks = {
        "entry_score": (
            result.parameters.entry_score
        ),
        "exit_score": (
            result.parameters.exit_score
        ),
        "stop_atr_multiple": (
            result.parameters.stop_atr_multiple
        ),
        "target_atr_multiple": (
            result.parameters.target_atr_multiple
        ),
        "maximum_holding_days": (
            float(
                result.parameters.maximum_holding_days
            )
        ),
        "position_percent": (
            result.parameters.position_percent
        ),
    }

    for field_name, expected_value in (
        parameter_checks.items()
    ):
        actual_value = safe_float(
            saved_parameters.get(
                field_name
            )
        )

        if actual_value is None:
            raise RuntimeError(
                f"저장된 parameters.{field_name} 값을 "
                "숫자로 변환할 수 없습니다."
            )

        if abs(
            actual_value
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"저장된 parameters.{field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    list_checks = {
        "allowed_operations": (
            result.allowed_operations
        ),
        "blocked_operations": (
            result.blocked_operations
        ),
        "reasons": result.reasons,
        "warnings": result.warnings,
        "next_actions": (
            result.next_actions
        ),
    }

    for field_name, expected_value in (
        list_checks.items()
    ):
        actual_value = report_payload.get(
            field_name
        )

        if actual_value != expected_value:
            raise RuntimeError(
                f"저장된 {field_name} 내용이 "
                "실행 결과와 일치하지 않습니다."
            )

    saved_report_path = Path(
        str(
            report_payload.get(
                "report_path"
            )
        )
    )

    saved_latest_path = Path(
        str(
            report_payload.get(
                "latest_path"
            )
        )
    )

    if saved_report_path != report_path:
        raise RuntimeError(
            "저장된 Report Path와 실제 경로가 "
            "일치하지 않습니다."
        )

    if saved_latest_path != latest_path:
        raise RuntimeError(
            "저장된 Latest Path와 실제 경로가 "
            "일치하지 않습니다."
        )


def print_test_result(
    result: StrategyRuntimeConfiguration,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.9 Runtime Provider 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V8.9 STRATEGY RUNTIME CONFIGURATION "
        "PROVIDER TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

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
    print("PERMISSIONS")
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

    for operation in result.allowed_operations:
        print(
            f"- {operation}"
        )

    print()
    print("BLOCKED OPERATIONS")
    print("-" * 140)

    for operation in result.blocked_operations:
        print(
            f"- {operation}"
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
        f"{report_path}"
    )

    print(
        f"Latest file                    : "
        f"{latest_path}"
    )

    print("=" * 140)


def print_validation_checks(
    result: StrategyRuntimeConfiguration,
    source_payload: dict[str, Any],
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 결과를 True/False로 출력합니다.
    """

    (
        expected_profile,
        expected_label,
    ) = calculate_expected_provider_profile(
        result.runtime_mode
    )

    source_all_checks_passed = bool(
        source_payload.get(
            "all_checks_passed"
        )
    )

    expected_all_checks = (
        result.source_checks_passed
        and result.permission_checks_passed
        and result.parameter_checks_passed
        and source_all_checks_passed
    )

    expected_status = (
        calculate_expected_provider_status(
            runtime_mode=result.runtime_mode,
            guard_status=result.guard_status,
            all_checks_passed=(
                result.all_checks_passed
            ),
        )
    )

    expected_ready = (
        calculate_expected_provider_ready(
            provider_status=(
                result.provider_status
            ),
            provider_profile=(
                result.provider_profile
            ),
        )
    )

    (
        expected_allowed,
        expected_blocked,
    ) = calculate_expected_operations(
        analysis_enabled=(
            result.analysis_enabled
        ),
        backtest_enabled=(
            result.backtest_enabled
        ),
        research_enabled=(
            result.research_enabled
        ),
        paper_execution_enabled=(
            result.paper_execution_enabled
        ),
        live_execution_enabled=(
            result.live_execution_enabled
        ),
    )

    source_path = Path(
        result.source_runtime_guard_file
    )

    source_symbol_matches = (
        str(
            source_payload.get(
                "symbol",
                "",
            )
        ).upper()
        == result.symbol
    )

    source_runtime_mode_matches = (
        str(
            source_payload.get(
                "runtime_mode",
                "",
            )
        ).upper()
        == result.runtime_mode
    )

    print()
    print("=" * 140)
    print("VALIDATION CHECKS")
    print("=" * 140)

    print(
        f"Version is V8.9                   : "
        f"{result.version == 'V8.9'}"
    )

    print(
        f"Provider status is valid          : "
        f"{(
            result.provider_status
            in VALID_PROVIDER_STATUSES
        )}"
    )

    print(
        f"Provider profile is valid         : "
        f"{(
            result.provider_profile
            in VALID_PROVIDER_PROFILES
        )}"
    )

    print(
        f"Runtime mode is valid             : "
        f"{result.runtime_mode in VALID_RUNTIME_MODES}"
    )

    print(
        f"Guard status is valid             : "
        f"{result.guard_status in VALID_GUARD_STATUSES}"
    )

    print(
        f"Source Runtime Guard exists       : "
        f"{source_path.exists()}"
    )

    print(
        f"Source Symbol matches             : "
        f"{source_symbol_matches}"
    )

    print(
        f"Source Runtime mode matches       : "
        f"{source_runtime_mode_matches}"
    )

    print(
        f"Provider profile matches          : "
        f"{result.provider_profile == expected_profile}"
    )

    print(
        f"Provider label matches            : "
        f"{result.provider_label == expected_label}"
    )

    print(
        f"Provider status matches           : "
        f"{result.provider_status == expected_status}"
    )

    print(
        f"Provider ready matches            : "
        f"{result.provider_ready == expected_ready}"
    )

    print(
        f"Source checks passed              : "
        f"{result.source_checks_passed}"
    )

    print(
        f"Permission checks passed          : "
        f"{result.permission_checks_passed}"
    )

    print(
        f"Parameter checks passed           : "
        f"{result.parameter_checks_passed}"
    )

    print(
        f"All checks match                  : "
        f"{result.all_checks_passed == expected_all_checks}"
    )

    print(
        f"Allowed operations match          : "
        f"{result.allowed_operations == expected_allowed}"
    )

    print(
        f"Blocked operations match          : "
        f"{result.blocked_operations == expected_blocked}"
    )

    print(
        f"Analysis operation matches        : "
        f"{(
            is_operation_allowed(
                result,
                'ANALYSIS',
            )
            == result.analysis_enabled
        )}"
    )

    print(
        f"Backtest operation matches        : "
        f"{(
            is_operation_allowed(
                result,
                'BACKTEST',
            )
            == result.backtest_enabled
        )}"
    )

    print(
        f"Research operation matches        : "
        f"{(
            is_operation_allowed(
                result,
                'RESEARCH',
            )
            == result.research_enabled
        )}"
    )

    print(
        f"Paper operation matches           : "
        f"{(
            is_operation_allowed(
                result,
                'PAPER_EXECUTION',
            )
            == result.paper_execution_enabled
        )}"
    )

    print(
        f"Live operation matches            : "
        f"{(
            is_operation_allowed(
                result,
                'LIVE_EXECUTION',
            )
            == result.live_execution_enabled
        )}"
    )

    print(
        f"Paper block flag matches          : "
        f"{(
            result.paper_execution_blocked
            == (
                not result.paper_execution_enabled
            )
        )}"
    )

    print(
        f"Live block flag matches           : "
        f"{(
            result.live_execution_blocked
            == (
                not result.live_execution_enabled
            )
        )}"
    )

    print(
        f"Entry is above Exit               : "
        f"{(
            result.parameters.entry_score
            > result.parameters.exit_score
        )}"
    )

    print(
        f"Stop ATR is safe                  : "
        f"{(
            0.50
            <= result.parameters.stop_atr_multiple
            <= 5.00
        )}"
    )

    print(
        f"Target ATR is safe                : "
        f"{(
            0.50
            <= result.parameters.target_atr_multiple
            <= 10.00
        )}"
    )

    print(
        f"Holding days are safe             : "
        f"{(
            1
            <= result.parameters.maximum_holding_days
            <= 90
        )}"
    )

    print(
        f"Position percent is safe          : "
        f"{(
            0.0
            < result.parameters.position_percent
            <= 25.0
        )}"
    )

    print(
        f"Parameters are immutable          : "
        f"True"
    )

    print(
        f"Reasons exist                     : "
        f"{bool(result.reasons)}"
    )

    print(
        f"Warnings exist                    : "
        f"{bool(result.warnings)}"
    )

    print(
        f"Next actions exist                : "
        f"{bool(result.next_actions)}"
    )

    print(
        f"Report file exists                : "
        f"{report_path.exists()}"
    )

    print(
        f"Latest file exists                : "
        f"{latest_path.exists()}"
    )

    print("=" * 140)


def main() -> None:
    """
    V8.9 Strategy Runtime Provider 통합 테스트입니다.

    검사 항목:

    1. V8.8 Runtime Guard Latest 파일 로딩
    2. 원본 파일 버전 및 Symbol 확인
    3. Provider Profile 변환 확인
    4. Provider Status 계산 확인
    5. 전략 파라미터 변환 확인
    6. 파라미터 불변성 확인
    7. 분석·백테스트·연구 권한 확인
    8. 모의투자·실거래 차단 확인
    9. Operation Helper 함수 확인
    10. Runtime Provider JSON 저장 및 검증
    """

    symbol = "AAPL"

    print_test_header()

    try:
        result = run_strategy_runtime_provider(
            symbol=symbol,
        )

        (
            report_path,
            latest_path,
        ) = save_strategy_runtime_provider(
            result
        )

        # 저장 경로가 객체에 반영된 후
        # Provider 결과를 다시 출력합니다.
        print_strategy_runtime_provider(
            result
        )

        validate_result_structure(
            result
        )

        validate_parameters_are_immutable(
            result.parameters
        )

        source_payload = validate_source_runtime_guard(
            result
        )

        validate_source_parameter_matches(
            result=result,
            source_payload=source_payload,
        )

        validate_source_permission_matches(
            result=result,
            source_payload=source_payload,
        )

        validate_provider_profile(
            result
        )

        validate_parameter_checks(
            result
        )

        validate_permission_checks(
            result
        )

        validate_operation_lists(
            result
        )

        validate_operation_helpers(
            result
        )

        validate_get_runtime_parameters(
            result
        )

        validate_provider_status_result(
            result=result,
            source_payload=source_payload,
        )

        validate_current_analysis_result(
            result
        )

        validate_saved_files(
            result=result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_test_result(
            result=result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_validation_checks(
            result=result,
            source_payload=source_payload,
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V8.9 strategy runtime provider "
            "test completed successfully."
        )

        if result.provider_profile == "ANALYSIS":
            print(
                "분석·백테스트·연구용 Runtime 설정을 "
                "정상적으로 제공했습니다."
            )

            print(
                "모의투자와 실거래 작업은 정상적으로 "
                "차단되었습니다."
            )

        elif result.provider_profile == "RESEARCH":
            print(
                "연구 전용 Runtime 설정을 "
                "정상적으로 제공했습니다."
            )

        elif result.provider_profile == "PAPER":
            print(
                "모의투자 Runtime 설정을 정상적으로 "
                "제공했으며 실거래는 차단했습니다."
            )

        elif result.provider_profile == "LIVE":
            print(
                "실거래 Runtime 설정을 제공할 수 있는 "
                "상태로 확인되었습니다."
            )

        else:
            print(
                "현재 Runtime 설정은 사용 불가능한 상태로 "
                "정상 차단되었습니다."
            )

        print(
            "주의: 이 Provider는 전략 파라미터와 권한만 "
            "제공하며 실제 증권 주문이나 자동 매매를 "
            "실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V8.9 Strategy Runtime Provider "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V8.9 STRATEGY RUNTIME PROVIDER ERROR"
        )
        print("=" * 140)

        print(
            f"Error type   : "
            f"{type(error).__name__}"
        )

        print(
            f"Error message: "
            f"{error}"
        )


if __name__ == "__main__":
    main()