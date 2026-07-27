import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

from backtest.strategy_runtime_provider import (
    StrategyRuntimeConfiguration,
    run_strategy_runtime_provider,
    save_strategy_runtime_provider,
)
from backtest.trading_engine_integration import (
    VALID_ENGINE_MODES,
    VALID_ENGINE_STATUSES,
    TradingEngineIntegrationResult,
    TradingEngineParameters,
    build_engine_operations,
    convert_runtime_parameters,
    determine_engine_mode,
    determine_engine_status,
    is_engine_operation_allowed,
    print_trading_engine_integration,
    require_engine_operation,
    run_trading_engine_integration,
    save_trading_engine_integration,
    validate_engine_parameters,
    validate_engine_permissions,
)


VALID_ENGINE_OPERATIONS = {
    "SIGNAL_ANALYSIS",
    "BACKTEST",
    "RESEARCH",
    "PAPER_ORDER_EXECUTION",
    "LIVE_ORDER_EXECUTION",
}


VALID_PROVIDER_PROFILES = {
    "LIVE",
    "PAPER",
    "ANALYSIS",
    "RESEARCH",
    "NONE",
}


VALID_RUNTIME_MODES = {
    "LIVE_READY",
    "PAPER_READY",
    "ANALYSIS_ONLY",
    "RESEARCH_ONLY",
    "BLOCKED",
}


def print_test_header() -> None:
    """
    V9.0 Trading Engine Integration 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V9.0 "
        "TRADING ENGINE INTEGRATION TEST"
    )
    print("=" * 140)


def load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽고 Dictionary로 반환합니다.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON 파일이 없습니다: {file_path}"
        )

    if file_path.stat().st_size <= 0:
        raise RuntimeError(
            f"JSON 파일이 비어 있습니다: {file_path}"
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
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


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


def calculate_expected_engine_mode(
    provider_profile: str,
) -> tuple[str, str]:
    """
    Provider Profile에서 예상되는 Engine Mode와 Label을
    독립적으로 계산합니다.
    """

    normalized_profile = (
        provider_profile
        .strip()
        .upper()
    )

    mapping = {
        "LIVE": (
            "LIVE_ENGINE",
            "실거래 엔진",
        ),
        "PAPER": (
            "PAPER_ENGINE",
            "모의투자 엔진",
        ),
        "ANALYSIS": (
            "ANALYSIS_ENGINE",
            "분석 및 백테스트 엔진",
        ),
        "RESEARCH": (
            "RESEARCH_ENGINE",
            "연구 전용 엔진",
        ),
        "NONE": (
            "BLOCKED_ENGINE",
            "사용 불가능 엔진",
        ),
    }

    return mapping.get(
        normalized_profile,
        (
            "BLOCKED_ENGINE",
            "사용 불가능 엔진",
        ),
    )


def calculate_expected_engine_status(
    engine_mode: str,
    provider_ready: bool,
    all_checks_passed: bool,
) -> str:
    """
    예상 Engine Status를 독립적으로 계산합니다.
    """

    if not all_checks_passed:
        return "FAILED"

    if (
        not provider_ready
        or engine_mode == "BLOCKED_ENGINE"
    ):
        return "BLOCKED"

    if engine_mode in {
        "ANALYSIS_ENGINE",
        "RESEARCH_ENGINE",
    }:
        return "LIMITED"

    return "READY"


def calculate_expected_engine_operations(
    analysis_allowed: bool,
    backtest_allowed: bool,
    research_allowed: bool,
    paper_execution_allowed: bool,
    live_execution_allowed: bool,
) -> tuple[
    list[str],
    list[str],
]:
    """
    권한에서 예상되는 Engine Operation 목록을 계산합니다.
    """

    operation_map = {
        "SIGNAL_ANALYSIS": analysis_allowed,
        "BACKTEST": backtest_allowed,
        "RESEARCH": research_allowed,
        "PAPER_ORDER_EXECUTION": (
            paper_execution_allowed
        ),
        "LIVE_ORDER_EXECUTION": (
            live_execution_allowed
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


def validate_parameter_structure(
    parameters: TradingEngineParameters,
) -> None:
    """
    TradingEngineParameters의 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        parameters,
        TradingEngineParameters,
    ):
        raise RuntimeError(
            "parameters가 TradingEngineParameters "
            "형식이 아닙니다."
        )

    float_fields = {
        "entry_score": (
            parameters.entry_score
        ),
        "exit_score": (
            parameters.exit_score
        ),
        "stop_atr_multiple": (
            parameters.stop_atr_multiple
        ),
        "target_atr_multiple": (
            parameters.target_atr_multiple
        ),
        "position_percent": (
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
            "maximum_holding_days가 int 형식이 아닙니다."
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
            "TradingEngineParameters.to_dict()의 구조가 "
            "예상 결과와 일치하지 않습니다."
        )


def validate_parameters_are_immutable(
    parameters: TradingEngineParameters,
) -> None:
    """
    TradingEngineParameters가 frozen Dataclass인지 검사합니다.
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
            "TradingEngineParameters 값을 직접 변경할 수 있습니다."
        )

    if (
        parameters.entry_score
        != original_entry_score
    ):
        raise RuntimeError(
            "불변 파라미터의 Entry Score가 변경되었습니다."
        )


def validate_result_structure(
    result: TradingEngineIntegrationResult,
) -> None:
    """
    V9.0 결과의 기본 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        result,
        TradingEngineIntegrationResult,
    ):
        raise RuntimeError(
            "결과가 TradingEngineIntegrationResult "
            "형식이 아닙니다."
        )

    if result.version != "V9.0":
        raise RuntimeError(
            f"버전이 V9.0이 아닙니다: {result.version}"
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

    if result.engine_status not in VALID_ENGINE_STATUSES:
        raise RuntimeError(
            "올바르지 않은 Engine Status입니다: "
            f"{result.engine_status}"
        )

    if result.engine_mode not in VALID_ENGINE_MODES:
        raise RuntimeError(
            "올바르지 않은 Engine Mode입니다: "
            f"{result.engine_mode}"
        )

    if not result.engine_label:
        raise RuntimeError(
            "Engine Label이 비어 있습니다."
        )

    if result.runtime_mode not in VALID_RUNTIME_MODES:
        raise RuntimeError(
            "올바르지 않은 Runtime Mode입니다: "
            f"{result.runtime_mode}"
        )

    if (
        result.provider_profile
        not in VALID_PROVIDER_PROFILES
    ):
        raise RuntimeError(
            "올바르지 않은 Provider Profile입니다: "
            f"{result.provider_profile}"
        )

    validate_parameter_structure(
        result.parameters
    )

    boolean_fields = {
        "configuration_loaded": (
            result.configuration_loaded
        ),
        "signal_engine_ready": (
            result.signal_engine_ready
        ),
        "risk_engine_ready": (
            result.risk_engine_ready
        ),
        "backtest_engine_ready": (
            result.backtest_engine_ready
        ),
        "research_engine_ready": (
            result.research_engine_ready
        ),
        "order_execution_ready": (
            result.order_execution_ready
        ),
        "paper_execution_ready": (
            result.paper_execution_ready
        ),
        "live_execution_ready": (
            result.live_execution_ready
        ),
        "analysis_allowed": (
            result.analysis_allowed
        ),
        "backtest_allowed": (
            result.backtest_allowed
        ),
        "research_allowed": (
            result.research_allowed
        ),
        "paper_execution_allowed": (
            result.paper_execution_allowed
        ),
        "live_execution_allowed": (
            result.live_execution_allowed
        ),
        "engine_checks_passed": (
            result.engine_checks_passed
        ),
        "parameter_checks_passed": (
            result.parameter_checks_passed
        ),
        "permission_checks_passed": (
            result.permission_checks_passed
        ),
        "all_checks_passed": (
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
        "allowed_engine_operations": (
            result.allowed_engine_operations
        ),
        "blocked_engine_operations": (
            result.blocked_engine_operations
        ),
        "reasons": result.reasons,
        "warnings": result.warnings,
        "next_actions": result.next_actions,
    }

    for field_name, value in list_fields.items():
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


def validate_runtime_provider_matches(
    result: TradingEngineIntegrationResult,
    runtime_provider: StrategyRuntimeConfiguration,
) -> None:
    """
    V9.0 결과가 V8.9 Runtime Provider와 일치하는지 검사합니다.
    """

    if result.symbol != runtime_provider.symbol:
        raise RuntimeError(
            "V9.0 Symbol이 Runtime Provider와 "
            "일치하지 않습니다."
        )

    if (
        result.runtime_mode
        != runtime_provider.runtime_mode
    ):
        raise RuntimeError(
            "Runtime Mode가 Runtime Provider와 "
            "일치하지 않습니다."
        )

    if (
        result.provider_status
        != runtime_provider.provider_status
    ):
        raise RuntimeError(
            "Provider Status가 Runtime Provider와 "
            "일치하지 않습니다."
        )

    if (
        result.provider_profile
        != runtime_provider.provider_profile
    ):
        raise RuntimeError(
            "Provider Profile이 Runtime Provider와 "
            "일치하지 않습니다."
        )

    if (
        result.strategy_source
        != runtime_provider.strategy_source
    ):
        raise RuntimeError(
            "Strategy Source가 Runtime Provider와 "
            "일치하지 않습니다."
        )

    if (
        result.strategy_status
        != runtime_provider.strategy_status
    ):
        raise RuntimeError(
            "Strategy Status가 Runtime Provider와 "
            "일치하지 않습니다."
        )

    if (
        result.strategy_name
        != runtime_provider.strategy_name
    ):
        raise RuntimeError(
            "Strategy Name이 Runtime Provider와 "
            "일치하지 않습니다."
        )

    if (
        result.strategy_type
        != runtime_provider.strategy_type
    ):
        raise RuntimeError(
            "Strategy Type이 Runtime Provider와 "
            "일치하지 않습니다."
        )


def validate_parameter_conversion(
    result: TradingEngineIntegrationResult,
    runtime_provider: StrategyRuntimeConfiguration,
) -> None:
    """
    Runtime Provider 파라미터가 Engine 파라미터로
    정확히 변환되었는지 검사합니다.
    """

    converted_parameters = convert_runtime_parameters(
        runtime_provider.parameters
    )

    if converted_parameters != result.parameters:
        raise RuntimeError(
            "convert_runtime_parameters 결과가 "
            "실제 Engine 파라미터와 일치하지 않습니다."
        )

    comparisons = {
        "entry_score": (
            result.parameters.entry_score,
            runtime_provider.parameters.entry_score,
        ),
        "exit_score": (
            result.parameters.exit_score,
            runtime_provider.parameters.exit_score,
        ),
        "stop_atr_multiple": (
            result.parameters.stop_atr_multiple,
            runtime_provider.parameters.stop_atr_multiple,
        ),
        "target_atr_multiple": (
            result.parameters.target_atr_multiple,
            runtime_provider.parameters.target_atr_multiple,
        ),
        "maximum_holding_days": (
            float(
                result.parameters.maximum_holding_days
            ),
            float(
                runtime_provider
                .parameters
                .maximum_holding_days
            ),
        ),
        "position_percent": (
            result.parameters.position_percent,
            runtime_provider.parameters.position_percent,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in comparisons.items():
        if abs(
            float(actual_value)
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"{field_name} 변환 결과가 일치하지 않습니다."
            )


def validate_engine_mode_result(
    result: TradingEngineIntegrationResult,
) -> None:
    """
    Provider Profile에서 Engine Mode가 정상 결정되었는지 검사합니다.
    """

    (
        expected_mode,
        expected_label,
    ) = calculate_expected_engine_mode(
        result.provider_profile
    )

    module_mode, module_label = determine_engine_mode(
        result.provider_profile
    )

    if (
        module_mode != expected_mode
        or module_label != expected_label
    ):
        raise RuntimeError(
            "determine_engine_mode 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.engine_mode != expected_mode:
        raise RuntimeError(
            "Engine Mode가 예상 결과와 일치하지 않습니다. "
            f"Expected={expected_mode}, "
            f"Actual={result.engine_mode}"
        )

    if result.engine_label != expected_label:
        raise RuntimeError(
            "Engine Label이 예상 결과와 일치하지 않습니다."
        )


def validate_engine_parameter_checks(
    result: TradingEngineIntegrationResult,
) -> None:
    """
    Engine 파라미터 검사 결과를 확인합니다.
    """

    (
        expected_passed,
        expected_errors,
    ) = validate_engine_parameters(
        result.parameters
    )

    if (
        result.parameter_checks_passed
        != expected_passed
    ):
        raise RuntimeError(
            "Parameter Checks Passed가 실제 검사 결과와 "
            "일치하지 않습니다."
        )

    if expected_errors:
        for error_message in expected_errors:
            warning_exists = any(
                error_message in str(warning)
                for warning in result.warnings
            )

            if not warning_exists:
                raise RuntimeError(
                    "Parameter Error가 Warnings에 없습니다: "
                    f"{error_message}"
                )

    if (
        result.parameters.entry_score
        <= result.parameters.exit_score
    ):
        raise RuntimeError(
            "Entry Score는 Exit Score보다 높아야 합니다."
        )

    if not (
        0.50
        <= result.parameters.stop_atr_multiple
        <= 5.00
    ):
        raise RuntimeError(
            "Stop ATR이 안전 범위를 벗어났습니다."
        )

    if not (
        0.50
        <= result.parameters.target_atr_multiple
        <= 10.00
    ):
        raise RuntimeError(
            "Target ATR이 안전 범위를 벗어났습니다."
        )

    if not (
        1
        <= result.parameters.maximum_holding_days
        <= 90
    ):
        raise RuntimeError(
            "Maximum Holding Days가 안전 범위를 벗어났습니다."
        )

    if not (
        0.0
        < result.parameters.position_percent
        <= 25.0
    ):
        raise RuntimeError(
            "Position Percent가 안전 범위를 벗어났습니다."
        )


def validate_engine_permission_checks(
    result: TradingEngineIntegrationResult,
) -> None:
    """
    Engine Mode와 권한의 일관성을 검사합니다.
    """

    (
        expected_passed,
        expected_errors,
    ) = validate_engine_permissions(
        engine_mode=result.engine_mode,
        analysis_allowed=result.analysis_allowed,
        backtest_allowed=result.backtest_allowed,
        research_allowed=result.research_allowed,
        paper_execution_allowed=(
            result.paper_execution_allowed
        ),
        live_execution_allowed=(
            result.live_execution_allowed
        ),
    )

    if (
        result.permission_checks_passed
        != expected_passed
    ):
        raise RuntimeError(
            "Permission Checks Passed가 실제 검사 결과와 "
            "일치하지 않습니다."
        )

    if expected_errors:
        for error_message in expected_errors:
            warning_exists = any(
                error_message in str(warning)
                for warning in result.warnings
            )

            if not warning_exists:
                raise RuntimeError(
                    "Permission Error가 Warnings에 없습니다: "
                    f"{error_message}"
                )


def validate_engine_operations(
    result: TradingEngineIntegrationResult,
) -> None:
    """
    허용 및 차단 Engine Operation 목록을 검사합니다.
    """

    (
        expected_allowed,
        expected_blocked,
    ) = calculate_expected_engine_operations(
        analysis_allowed=result.analysis_allowed,
        backtest_allowed=result.backtest_allowed,
        research_allowed=result.research_allowed,
        paper_execution_allowed=(
            result.paper_execution_allowed
        ),
        live_execution_allowed=(
            result.live_execution_allowed
        ),
    )

    (
        module_allowed,
        module_blocked,
    ) = build_engine_operations(
        analysis_allowed=result.analysis_allowed,
        backtest_allowed=result.backtest_allowed,
        research_allowed=result.research_allowed,
        paper_execution_allowed=(
            result.paper_execution_allowed
        ),
        live_execution_allowed=(
            result.live_execution_allowed
        ),
    )

    if module_allowed != expected_allowed:
        raise RuntimeError(
            "build_engine_operations의 Allowed 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if module_blocked != expected_blocked:
        raise RuntimeError(
            "build_engine_operations의 Blocked 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if (
        result.allowed_engine_operations
        != expected_allowed
    ):
        raise RuntimeError(
            "Allowed Engine Operations가 예상 결과와 "
            "일치하지 않습니다."
        )

    if (
        result.blocked_engine_operations
        != expected_blocked
    ):
        raise RuntimeError(
            "Blocked Engine Operations가 예상 결과와 "
            "일치하지 않습니다."
        )

    allowed_set = set(
        result.allowed_engine_operations
    )

    blocked_set = set(
        result.blocked_engine_operations
    )

    if allowed_set & blocked_set:
        raise RuntimeError(
            "동일한 Operation이 Allowed와 Blocked에 "
            "동시에 포함되어 있습니다."
        )

    if (
        allowed_set | blocked_set
        != VALID_ENGINE_OPERATIONS
    ):
        raise RuntimeError(
            "Allowed와 Blocked Operation의 합이 "
            "전체 Operation 목록과 일치하지 않습니다."
        )


def validate_operation_helpers(
    result: TradingEngineIntegrationResult,
) -> None:
    """
    Engine Operation Helper 함수를 검사합니다.
    """

    for operation in VALID_ENGINE_OPERATIONS:
        expected_allowed = (
            operation
            in result.allowed_engine_operations
        )

        actual_allowed = (
            is_engine_operation_allowed(
                result,
                operation,
            )
        )

        if actual_allowed != expected_allowed:
            raise RuntimeError(
                f"is_engine_operation_allowed 결과가 "
                f"{operation} 권한과 일치하지 않습니다."
            )

        if expected_allowed:
            try:
                require_engine_operation(
                    result,
                    operation,
                )

            except Exception as error:
                raise RuntimeError(
                    f"허용된 {operation} 작업에서 "
                    "require_engine_operation이 오류를 "
                    f"발생시켰습니다: {error}"
                ) from error

        else:
            blocked_correctly = False

            try:
                require_engine_operation(
                    result,
                    operation,
                )

            except RuntimeError:
                blocked_correctly = True

            if not blocked_correctly:
                raise RuntimeError(
                    f"차단된 {operation} 작업을 "
                    "require_engine_operation이 허용했습니다."
                )

    invalid_operation_blocked = False

    try:
        require_engine_operation(
            result,
            "INVALID_ENGINE_OPERATION",
        )

    except ValueError:
        invalid_operation_blocked = True

    if not invalid_operation_blocked:
        raise RuntimeError(
            "알 수 없는 Engine Operation이 차단되지 않았습니다."
        )


def validate_readiness_flags(
    result: TradingEngineIntegrationResult,
    runtime_provider: StrategyRuntimeConfiguration,
) -> None:
    """
    Engine 준비 상태 Flag를 독립적으로 계산하여 검사합니다.
    """

    expected_configuration_loaded = (
        runtime_provider.provider_ready
    )

    expected_signal_ready = (
        expected_configuration_loaded
        and result.analysis_allowed
        and result.parameter_checks_passed
    )

    expected_risk_ready = (
        expected_configuration_loaded
        and result.parameter_checks_passed
    )

    expected_backtest_ready = (
        expected_configuration_loaded
        and result.backtest_allowed
        and result.parameter_checks_passed
    )

    expected_research_ready = (
        expected_configuration_loaded
        and result.research_allowed
        and result.parameter_checks_passed
    )

    expected_paper_ready = (
        expected_configuration_loaded
        and result.paper_execution_allowed
        and result.parameter_checks_passed
        and result.permission_checks_passed
    )

    expected_live_ready = (
        expected_configuration_loaded
        and result.live_execution_allowed
        and result.parameter_checks_passed
        and result.permission_checks_passed
        and not runtime_provider.manual_approval_required
    )

    expected_order_ready = (
        expected_paper_ready
        or expected_live_ready
    )

    expected_engine_checks = (
        expected_configuration_loaded
        and expected_signal_ready
        and expected_risk_ready
    )

    expected_all_checks = (
        runtime_provider.all_checks_passed
        and expected_engine_checks
        and result.parameter_checks_passed
        and result.permission_checks_passed
    )

    readiness_checks = {
        "Configuration Loaded": (
            result.configuration_loaded,
            expected_configuration_loaded,
        ),
        "Signal Engine Ready": (
            result.signal_engine_ready,
            expected_signal_ready,
        ),
        "Risk Engine Ready": (
            result.risk_engine_ready,
            expected_risk_ready,
        ),
        "Backtest Engine Ready": (
            result.backtest_engine_ready,
            expected_backtest_ready,
        ),
        "Research Engine Ready": (
            result.research_engine_ready,
            expected_research_ready,
        ),
        "Paper Execution Ready": (
            result.paper_execution_ready,
            expected_paper_ready,
        ),
        "Live Execution Ready": (
            result.live_execution_ready,
            expected_live_ready,
        ),
        "Order Execution Ready": (
            result.order_execution_ready,
            expected_order_ready,
        ),
        "Engine Checks Passed": (
            result.engine_checks_passed,
            expected_engine_checks,
        ),
        "All Checks Passed": (
            result.all_checks_passed,
            expected_all_checks,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in readiness_checks.items():
        if actual_value != expected_value:
            raise RuntimeError(
                f"{field_name}가 예상 결과와 일치하지 않습니다. "
                f"Expected={expected_value}, "
                f"Actual={actual_value}"
            )


def validate_engine_status_result(
    result: TradingEngineIntegrationResult,
    runtime_provider: StrategyRuntimeConfiguration,
) -> None:
    """
    Engine Status 계산 결과를 검사합니다.
    """

    expected_status = (
        calculate_expected_engine_status(
            engine_mode=result.engine_mode,
            provider_ready=(
                runtime_provider.provider_ready
            ),
            all_checks_passed=(
                result.all_checks_passed
            ),
        )
    )

    module_status = determine_engine_status(
        engine_mode=result.engine_mode,
        provider_ready=(
            runtime_provider.provider_ready
        ),
        all_checks_passed=(
            result.all_checks_passed
        ),
    )

    if module_status != expected_status:
        raise RuntimeError(
            "determine_engine_status 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.engine_status != expected_status:
        raise RuntimeError(
            "Engine Status가 예상 결과와 일치하지 않습니다. "
            f"Expected={expected_status}, "
            f"Actual={result.engine_status}"
        )


def validate_current_analysis_engine(
    result: TradingEngineIntegrationResult,
) -> None:
    """
    현재 ANALYSIS_ONLY 상태에서 예상되는 결과를 검사합니다.
    """

    if result.runtime_mode != "ANALYSIS_ONLY":
        return

    if result.engine_mode != "ANALYSIS_ENGINE":
        raise RuntimeError(
            "ANALYSIS_ONLY인데 Engine Mode가 "
            "ANALYSIS_ENGINE이 아닙니다."
        )

    if result.engine_status != "LIMITED":
        raise RuntimeError(
            "ANALYSIS_ENGINE인데 Engine Status가 "
            "LIMITED가 아닙니다."
        )

    if result.engine_label != "분석 및 백테스트 엔진":
        raise RuntimeError(
            "Analysis Engine Label이 올바르지 않습니다."
        )

    if not result.configuration_loaded:
        raise RuntimeError(
            "Runtime Configuration이 로드되지 않았습니다."
        )

    if not result.signal_engine_ready:
        raise RuntimeError(
            "Signal Engine이 준비되지 않았습니다."
        )

    if not result.risk_engine_ready:
        raise RuntimeError(
            "Risk Engine이 준비되지 않았습니다."
        )

    if not result.backtest_engine_ready:
        raise RuntimeError(
            "Backtest Engine이 준비되지 않았습니다."
        )

    if not result.research_engine_ready:
        raise RuntimeError(
            "Research Engine이 준비되지 않았습니다."
        )

    if result.order_execution_ready:
        raise RuntimeError(
            "ANALYSIS_ENGINE에서 주문 실행 준비가 "
            "활성화되었습니다."
        )

    if result.paper_execution_ready:
        raise RuntimeError(
            "ANALYSIS_ENGINE에서 모의 주문 준비가 "
            "활성화되었습니다."
        )

    if result.live_execution_ready:
        raise RuntimeError(
            "ANALYSIS_ENGINE에서 실거래 준비가 "
            "활성화되었습니다."
        )

    expected_allowed = [
        "SIGNAL_ANALYSIS",
        "BACKTEST",
        "RESEARCH",
    ]

    expected_blocked = [
        "PAPER_ORDER_EXECUTION",
        "LIVE_ORDER_EXECUTION",
    ]

    if (
        result.allowed_engine_operations
        != expected_allowed
    ):
        raise RuntimeError(
            "ANALYSIS_ENGINE의 Allowed Operations가 "
            "예상 결과와 일치하지 않습니다."
        )

    if (
        result.blocked_engine_operations
        != expected_blocked
    ):
        raise RuntimeError(
            "ANALYSIS_ENGINE의 Blocked Operations가 "
            "예상 결과와 일치하지 않습니다."
        )

    execution_warning_exists = any(
        (
            "모의 주문"
            in str(warning)
        )
        or (
            "실거래 주문"
            in str(warning)
        )
        or (
            "실제 주문"
            in str(warning)
        )
        for warning in result.warnings
    )

    if not execution_warning_exists:
        raise RuntimeError(
            "Warnings에 주문 실행 차단 설명이 없습니다."
        )


def validate_saved_files(
    result: TradingEngineIntegrationResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.0 JSON 저장 결과를 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            f"V9.0 Report 파일이 없습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            f"V9.0 Latest 파일이 없습니다: {latest_path}"
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "V9.0 Report 파일과 Latest 파일의 내용이 "
            "일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_runtime_provider_file",
        "engine_status",
        "engine_mode",
        "engine_label",
        "runtime_mode",
        "provider_status",
        "provider_profile",
        "strategy_source",
        "strategy_status",
        "strategy_name",
        "strategy_type",
        "parameters",
        "configuration_loaded",
        "signal_engine_ready",
        "risk_engine_ready",
        "backtest_engine_ready",
        "research_engine_ready",
        "order_execution_ready",
        "paper_execution_ready",
        "live_execution_ready",
        "analysis_allowed",
        "backtest_allowed",
        "research_allowed",
        "paper_execution_allowed",
        "live_execution_allowed",
        "engine_checks_passed",
        "parameter_checks_passed",
        "permission_checks_passed",
        "all_checks_passed",
        "allowed_engine_operations",
        "blocked_engine_operations",
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
            "저장된 V9.0 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    text_checks = {
        "version": result.version,
        "symbol": result.symbol,
        "engine_status": result.engine_status,
        "engine_mode": result.engine_mode,
        "engine_label": result.engine_label,
        "runtime_mode": result.runtime_mode,
        "provider_status": result.provider_status,
        "provider_profile": result.provider_profile,
        "strategy_source": result.strategy_source,
        "strategy_status": result.strategy_status,
    }

    for field_name, expected_value in text_checks.items():
        actual_value = report_payload.get(
            field_name
        )

        if str(actual_value) != str(expected_value):
            raise RuntimeError(
                f"저장된 {field_name} 값이 실행 결과와 "
                "일치하지 않습니다."
            )

    boolean_checks = {
        "configuration_loaded": (
            result.configuration_loaded
        ),
        "signal_engine_ready": (
            result.signal_engine_ready
        ),
        "risk_engine_ready": (
            result.risk_engine_ready
        ),
        "backtest_engine_ready": (
            result.backtest_engine_ready
        ),
        "research_engine_ready": (
            result.research_engine_ready
        ),
        "order_execution_ready": (
            result.order_execution_ready
        ),
        "paper_execution_ready": (
            result.paper_execution_ready
        ),
        "live_execution_ready": (
            result.live_execution_ready
        ),
        "analysis_allowed": (
            result.analysis_allowed
        ),
        "backtest_allowed": (
            result.backtest_allowed
        ),
        "research_allowed": (
            result.research_allowed
        ),
        "paper_execution_allowed": (
            result.paper_execution_allowed
        ),
        "live_execution_allowed": (
            result.live_execution_allowed
        ),
        "engine_checks_passed": (
            result.engine_checks_passed
        ),
        "parameter_checks_passed": (
            result.parameter_checks_passed
        ),
        "permission_checks_passed": (
            result.permission_checks_passed
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
                f"저장된 {field_name} 값이 실행 결과와 "
                "일치하지 않습니다."
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
                f"저장된 parameters.{field_name}를 "
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
        "allowed_engine_operations": (
            result.allowed_engine_operations
        ),
        "blocked_engine_operations": (
            result.blocked_engine_operations
        ),
        "reasons": result.reasons,
        "warnings": result.warnings,
        "next_actions": result.next_actions,
    }

    for field_name, expected_value in (
        list_checks.items()
    ):
        if (
            report_payload.get(field_name)
            != expected_value
        ):
            raise RuntimeError(
                f"저장된 {field_name} 값이 실행 결과와 "
                "일치하지 않습니다."
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
            "JSON 내부 Report Path와 실제 Report Path가 "
            "일치하지 않습니다."
        )

    if saved_latest_path != latest_path:
        raise RuntimeError(
            "JSON 내부 Latest Path와 실제 Latest Path가 "
            "일치하지 않습니다."
        )


def print_test_result(
    result: TradingEngineIntegrationResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    최종 V9.0 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V9.0 TRADING ENGINE INTEGRATION "
        "TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

    print(
        f"Engine status                  : "
        f"{result.engine_status}"
    )

    print(
        f"Engine mode                    : "
        f"{result.engine_mode}"
    )

    print(
        f"Engine label                   : "
        f"{result.engine_label}"
    )

    print(
        f"Runtime mode                   : "
        f"{result.runtime_mode}"
    )

    print(
        f"Provider status                : "
        f"{result.provider_status}"
    )

    print(
        f"Provider profile               : "
        f"{result.provider_profile}"
    )

    print()
    print("ENGINE READINESS")
    print("-" * 140)

    print(
        f"Configuration loaded           : "
        f"{result.configuration_loaded}"
    )

    print(
        f"Signal engine ready            : "
        f"{result.signal_engine_ready}"
    )

    print(
        f"Risk engine ready              : "
        f"{result.risk_engine_ready}"
    )

    print(
        f"Backtest engine ready          : "
        f"{result.backtest_engine_ready}"
    )

    print(
        f"Research engine ready          : "
        f"{result.research_engine_ready}"
    )

    print(
        f"Order execution ready          : "
        f"{result.order_execution_ready}"
    )

    print(
        f"Paper execution ready          : "
        f"{result.paper_execution_ready}"
    )

    print(
        f"Live execution ready           : "
        f"{result.live_execution_ready}"
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
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Engine checks passed           : "
        f"{result.engine_checks_passed}"
    )

    print(
        f"Parameter checks passed        : "
        f"{result.parameter_checks_passed}"
    )

    print(
        f"Permission checks passed       : "
        f"{result.permission_checks_passed}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("ALLOWED ENGINE OPERATIONS")
    print("-" * 140)

    for operation in result.allowed_engine_operations:
        print(
            f"- {operation}"
        )

    print()
    print("BLOCKED ENGINE OPERATIONS")
    print("-" * 140)

    for operation in result.blocked_engine_operations:
        print(
            f"- {operation}"
        )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Runtime Provider file   : "
        f"{result.source_runtime_provider_file}"
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
    result: TradingEngineIntegrationResult,
    runtime_provider: StrategyRuntimeConfiguration,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True/False로 출력합니다.
    """

    (
        expected_mode,
        expected_label,
    ) = calculate_expected_engine_mode(
        result.provider_profile
    )

    expected_status = (
        calculate_expected_engine_status(
            engine_mode=result.engine_mode,
            provider_ready=(
                runtime_provider.provider_ready
            ),
            all_checks_passed=(
                result.all_checks_passed
            ),
        )
    )

    (
        expected_allowed,
        expected_blocked,
    ) = calculate_expected_engine_operations(
        analysis_allowed=result.analysis_allowed,
        backtest_allowed=result.backtest_allowed,
        research_allowed=result.research_allowed,
        paper_execution_allowed=(
            result.paper_execution_allowed
        ),
        live_execution_allowed=(
            result.live_execution_allowed
        ),
    )

    source_provider_path = (
        Path(result.source_runtime_provider_file)
        if result.source_runtime_provider_file
        else None
    )

    print()
    print("=" * 140)
    print("VALIDATION CHECKS")
    print("=" * 140)

    checks = {
        "Version is V9.0": (
            result.version == "V9.0"
        ),
        "Engine status is valid": (
            result.engine_status
            in VALID_ENGINE_STATUSES
        ),
        "Engine mode is valid": (
            result.engine_mode
            in VALID_ENGINE_MODES
        ),
        "Provider profile is valid": (
            result.provider_profile
            in VALID_PROVIDER_PROFILES
        ),
        "Runtime mode is valid": (
            result.runtime_mode
            in VALID_RUNTIME_MODES
        ),
        "Engine mode matches": (
            result.engine_mode
            == expected_mode
        ),
        "Engine label matches": (
            result.engine_label
            == expected_label
        ),
        "Engine status matches": (
            result.engine_status
            == expected_status
        ),
        "Symbol matches provider": (
            result.symbol
            == runtime_provider.symbol
        ),
        "Runtime mode matches provider": (
            result.runtime_mode
            == runtime_provider.runtime_mode
        ),
        "Provider status matches": (
            result.provider_status
            == runtime_provider.provider_status
        ),
        "Provider profile matches": (
            result.provider_profile
            == runtime_provider.provider_profile
        ),
        "Configuration loaded": (
            result.configuration_loaded
        ),
        "Signal engine ready": (
            result.signal_engine_ready
        ),
        "Risk engine ready": (
            result.risk_engine_ready
        ),
        "Backtest engine ready": (
            result.backtest_engine_ready
        ),
        "Research engine ready": (
            result.research_engine_ready
        ),
        "Order execution blocked": (
            not result.order_execution_ready
            if result.engine_mode
            in {
                "ANALYSIS_ENGINE",
                "RESEARCH_ENGINE",
            }
            else True
        ),
        "Paper execution blocked": (
            not result.paper_execution_ready
            if not result.paper_execution_allowed
            else True
        ),
        "Live execution blocked": (
            not result.live_execution_ready
            if not result.live_execution_allowed
            else True
        ),
        "Engine checks passed": (
            result.engine_checks_passed
        ),
        "Parameter checks passed": (
            result.parameter_checks_passed
        ),
        "Permission checks passed": (
            result.permission_checks_passed
        ),
        "All checks passed": (
            result.all_checks_passed
        ),
        "Allowed operations match": (
            result.allowed_engine_operations
            == expected_allowed
        ),
        "Blocked operations match": (
            result.blocked_engine_operations
            == expected_blocked
        ),
        "Entry is above Exit": (
            result.parameters.entry_score
            > result.parameters.exit_score
        ),
        "Stop ATR is safe": (
            0.50
            <= result.parameters.stop_atr_multiple
            <= 5.00
        ),
        "Target ATR is safe": (
            0.50
            <= result.parameters.target_atr_multiple
            <= 10.00
        ),
        "Holding days are safe": (
            1
            <= result.parameters.maximum_holding_days
            <= 90
        ),
        "Position percent is safe": (
            0.0
            < result.parameters.position_percent
            <= 25.0
        ),
        "Parameters are immutable": True,
        "Reasons exist": bool(
            result.reasons
        ),
        "Warnings exist": bool(
            result.warnings
        ),
        "Next actions exist": bool(
            result.next_actions
        ),
        "Source provider file exists": (
            source_provider_path.exists()
            if source_provider_path
            else False
        ),
        "Report file exists": (
            report_path.exists()
        ),
        "Latest file exists": (
            latest_path.exists()
        ),
    }

    for check_name, check_result in checks.items():
        print(
            f"{check_name:<36}: {check_result}"
        )

    print("=" * 140)


def main() -> None:
    """
    V9.0 Trading Engine Integration 통합 테스트입니다.

    검사 항목:

    1. V8.9 Runtime Provider 실행 및 저장
    2. V9.0 Trading Engine Integration 실행
    3. Runtime Provider와 Engine 설정 비교
    4. 전략 파라미터 변환 검사
    5. Engine Mode 및 Status 검사
    6. Signal, Risk, Backtest, Research 준비 검사
    7. Paper 및 Live 실행 차단 검사
    8. Operation Helper 검사
    9. 파라미터 불변성 검사
    10. JSON Report 및 Latest 파일 검사
    """

    symbol = "AAPL"

    print_test_header()

    try:
        runtime_provider = (
            run_strategy_runtime_provider(
                symbol=symbol,
            )
        )

        (
            provider_report_path,
            provider_latest_path,
        ) = save_strategy_runtime_provider(
            runtime_provider
        )

        if not provider_report_path.exists():
            raise RuntimeError(
                "V8.9 Runtime Provider Report 파일이 없습니다."
            )

        if not provider_latest_path.exists():
            raise RuntimeError(
                "V8.9 Runtime Provider Latest 파일이 없습니다."
            )

        result = run_trading_engine_integration(
            symbol=symbol,
            runtime_provider=runtime_provider,
        )

        (
            report_path,
            latest_path,
        ) = save_trading_engine_integration(
            result
        )

        # 저장된 경로가 Result 객체에 반영된 후 다시 출력합니다.
        print_trading_engine_integration(
            result
        )

        validate_result_structure(
            result
        )

        validate_parameters_are_immutable(
            result.parameters
        )

        validate_runtime_provider_matches(
            result=result,
            runtime_provider=runtime_provider,
        )

        validate_parameter_conversion(
            result=result,
            runtime_provider=runtime_provider,
        )

        validate_engine_mode_result(
            result
        )

        validate_engine_parameter_checks(
            result
        )

        validate_engine_permission_checks(
            result
        )

        validate_engine_operations(
            result
        )

        validate_operation_helpers(
            result
        )

        validate_readiness_flags(
            result=result,
            runtime_provider=runtime_provider,
        )

        validate_engine_status_result(
            result=result,
            runtime_provider=runtime_provider,
        )

        validate_current_analysis_engine(
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
            runtime_provider=runtime_provider,
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V9.0 trading engine integration "
            "test completed successfully."
        )

        if result.engine_mode == "ANALYSIS_ENGINE":
            print(
                "Runtime Provider 전략을 분석·백테스트용 "
                "Trading Engine에 정상 연결했습니다."
            )

            print(
                "Signal, Risk, Backtest 및 Research Engine은 "
                "정상적으로 준비되었습니다."
            )

            print(
                "모의 주문과 실거래 주문은 정상적으로 "
                "차단되었습니다."
            )

        elif result.engine_mode == "RESEARCH_ENGINE":
            print(
                "Runtime Provider 전략을 연구 전용 Engine에 "
                "정상 연결했습니다."
            )

            print(
                "모든 주문 실행 기능은 차단되었습니다."
            )

        elif result.engine_mode == "PAPER_ENGINE":
            print(
                "Runtime Provider 전략을 모의투자 Engine에 "
                "정상 연결했습니다."
            )

            print(
                "실거래 주문 기능은 차단되었습니다."
            )

        elif result.engine_mode == "LIVE_ENGINE":
            print(
                "Runtime Provider 전략을 실거래 준비 Engine에 "
                "정상 연결했습니다."
            )

            print(
                "실제 주문 실행 전 수동 승인과 추가 안전 검사가 "
                "필요합니다."
            )

        else:
            print(
                "Runtime Provider 상태에 따라 Trading Engine이 "
                "정상적으로 차단되었습니다."
            )

        print(
            "주의: 이 테스트는 전략 설정과 Engine 준비 상태만 "
            "검증하며 실제 증권 주문이나 자동 매매를 "
            "실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V9.0 Trading Engine Integration "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V9.0 TRADING ENGINE INTEGRATION ERROR"
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