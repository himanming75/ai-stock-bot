import json
from pathlib import Path
from typing import Any

from backtest.strategy_runtime_guard import (
    DEFAULT_MAX_HOLDING_DAYS,
    DEFAULT_MAX_POSITION_PERCENT,
    DEFAULT_MAX_STOP_ATR,
    DEFAULT_MAX_TARGET_ATR,
    DEFAULT_MIN_STOP_ATR,
    DEFAULT_MIN_TARGET_ATR,
    VALID_CONFIGURATION_MODES,
    VALID_GUARD_STATUSES,
    VALID_RUNTIME_MODES,
    StrategyRuntimeGuardResult,
    determine_guard_status,
    determine_runtime_mode,
    evaluate_runtime_permissions,
    print_strategy_runtime_guard,
    run_strategy_runtime_guard,
    save_strategy_runtime_guard,
    validate_runtime_parameters,
)


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


def print_test_header() -> None:
    """
    V8.8 Strategy Runtime Guard
    테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V8.8 "
        "STRATEGY RUNTIME GUARD TEST"
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


def calculate_expected_runtime_mode(
    configuration_mode: str,
    configuration_ready: bool,
    execution_enabled: bool,
    paper_execution_enabled: bool,
    manual_approval_required: bool,
) -> tuple[str, str]:
    """
    Configuration 상태를 이용하여 예상되는
    Runtime Mode와 Label을 독립적으로 계산합니다.
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


def calculate_expected_permissions(
    runtime_mode: str,
) -> dict[str, bool]:
    """
    Runtime Mode에 따른 예상 권한을
    독립적으로 계산합니다.
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

    if normalized_mode in {
        "ANALYSIS_ONLY",
        "RESEARCH_ONLY",
    }:
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


def calculate_expected_guard_status(
    runtime_mode: str,
    all_checks_passed: bool,
) -> str:
    """
    Runtime Mode와 검사 결과를 이용해
    예상 Guard Status를 계산합니다.
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


def validate_result_structure(
    result: StrategyRuntimeGuardResult,
) -> None:
    """
    V8.8 Runtime Guard 결과의
    기본 구조와 자료형을 검사합니다.
    """

    if result.version != "V8.8":
        raise RuntimeError(
            "Runtime Guard 버전이 V8.8이 아닙니다: "
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

    if not result.source_configuration_file:
        raise RuntimeError(
            "Source Configuration File이 비어 있습니다."
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

    if not result.runtime_label:
        raise RuntimeError(
            "Runtime Label이 비어 있습니다."
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

    boolean_fields = {
        "Configuration Ready": (
            result.configuration_ready
        ),
        "Analysis Allowed": (
            result.analysis_allowed
        ),
        "Backtest Allowed": (
            result.backtest_allowed
        ),
        "Research Allowed": (
            result.research_allowed
        ),
        "Paper Execution Allowed": (
            result.paper_execution_allowed
        ),
        "Live Execution Allowed": (
            result.live_execution_allowed
        ),
        "Execution Enabled From Configuration": (
            result.execution_enabled_from_configuration
        ),
        "Paper Execution Enabled From Configuration": (
            result.paper_execution_enabled_from_configuration
        ),
        "Manual Approval Required": (
            result.manual_approval_required
        ),
        "Parameter Checks Passed": (
            result.parameter_checks_passed
        ),
        "Execution Checks Passed": (
            result.execution_checks_passed
        ),
        "Source Checks Passed": (
            result.source_checks_passed
        ),
        "All Checks Passed": (
            result.all_checks_passed
        ),
        "Live Execution Blocked": (
            result.live_execution_blocked
        ),
        "Paper Execution Blocked": (
            result.paper_execution_blocked
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

    float_fields = {
        "Entry Score": result.entry_score,
        "Exit Score": result.exit_score,
        "Stop ATR": result.stop_atr_multiple,
        "Target ATR": result.target_atr_multiple,
        "Position Percent": result.position_percent,
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
        result.maximum_holding_days,
        int,
    ):
        raise RuntimeError(
            "Maximum Holding Days가 int 형식이 아닙니다."
        )

    list_fields = {
        "Blocking Reasons": (
            result.blocking_reasons
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


def validate_source_configuration(
    result: StrategyRuntimeGuardResult,
) -> dict[str, Any]:
    """
    V8.7 Configuration 원본 파일과
    V8.8 Runtime Guard 결과를 비교합니다.
    """

    source_path = Path(
        result.source_configuration_file
    )

    if not source_path.exists():
        raise RuntimeError(
            "Source Configuration 파일이 "
            "존재하지 않습니다: "
            f"{source_path}"
        )

    if source_path.stat().st_size <= 0:
        raise RuntimeError(
            "Source Configuration 파일이 비어 있습니다."
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

    if source_version != "V8.7":
        raise RuntimeError(
            "Source Configuration 파일의 "
            "버전이 V8.7이 아닙니다."
        )

    source_symbol = str(
        source_payload.get(
            "symbol",
            "",
        )
    ).upper()

    if source_symbol != result.symbol:
        raise RuntimeError(
            "Source Configuration의 Symbol과 "
            "Runtime Guard Symbol이 일치하지 않습니다."
        )

    source_mode = str(
        source_payload.get(
            "configuration_mode",
            "",
        )
    ).upper()

    if (
        source_mode
        != result.configuration_mode
    ):
        raise RuntimeError(
            "Source Configuration Mode와 "
            "Runtime Guard의 Configuration Mode가 "
            "일치하지 않습니다."
        )

    source_strategy = str(
        source_payload.get(
            "strategy_source",
            "NONE",
        )
    )

    if source_strategy != result.strategy_source:
        raise RuntimeError(
            "Strategy Source가 원본 Configuration과 "
            "일치하지 않습니다."
        )

    source_status = str(
        source_payload.get(
            "strategy_status",
            "UNREGISTERED",
        )
    )

    if source_status != result.strategy_status:
        raise RuntimeError(
            "Strategy Status가 원본 Configuration과 "
            "일치하지 않습니다."
        )

    source_ready = bool(
        source_payload.get(
            "configuration_ready"
        )
    )

    if (
        source_ready
        != result.configuration_ready
    ):
        raise RuntimeError(
            "Configuration Ready 값이 원본 파일과 "
            "일치하지 않습니다."
        )

    return source_payload


def validate_runtime_mode(
    result: StrategyRuntimeGuardResult,
) -> None:
    """
    Configuration 상태가 Runtime Mode로
    정상 변환되었는지 검사합니다.
    """

    (
        expected_mode,
        expected_label,
    ) = calculate_expected_runtime_mode(
        configuration_mode=(
            result.configuration_mode
        ),
        configuration_ready=(
            result.configuration_ready
        ),
        execution_enabled=(
            result.execution_enabled_from_configuration
        ),
        paper_execution_enabled=(
            result.paper_execution_enabled_from_configuration
        ),
        manual_approval_required=(
            result.manual_approval_required
        ),
    )

    module_result = determine_runtime_mode(
        configuration_mode=(
            result.configuration_mode
        ),
        configuration_ready=(
            result.configuration_ready
        ),
        execution_enabled=(
            result.execution_enabled_from_configuration
        ),
        paper_execution_enabled=(
            result.paper_execution_enabled_from_configuration
        ),
        manual_approval_required=(
            result.manual_approval_required
        ),
    )

    if module_result != (
        expected_mode,
        expected_label,
    ):
        raise RuntimeError(
            "determine_runtime_mode 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.runtime_mode != expected_mode:
        raise RuntimeError(
            "Runtime Mode가 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_mode}, "
            f"Actual={result.runtime_mode}"
        )

    if result.runtime_label != expected_label:
        raise RuntimeError(
            "Runtime Label이 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_label}, "
            f"Actual={result.runtime_label}"
        )


def validate_runtime_parameters_result(
    result: StrategyRuntimeGuardResult,
) -> None:
    """
    Runtime 파라미터 검사 결과를 확인합니다.
    """

    (
        expected_passed,
        expected_errors,
    ) = validate_runtime_parameters(
        entry_score=result.entry_score,
        exit_score=result.exit_score,
        stop_atr_multiple=(
            result.stop_atr_multiple
        ),
        target_atr_multiple=(
            result.target_atr_multiple
        ),
        maximum_holding_days=(
            result.maximum_holding_days
        ),
        position_percent=(
            result.position_percent
        ),
    )

    if (
        result.parameter_checks_passed
        != expected_passed
    ):
        raise RuntimeError(
            "Parameter Checks Passed가 실제 검사 "
            "결과와 일치하지 않습니다."
        )

    if expected_errors:
        for error_message in expected_errors:
            if (
                error_message
                not in result.blocking_reasons
            ):
                raise RuntimeError(
                    "파라미터 오류가 Blocking Reasons에 "
                    "포함되지 않았습니다: "
                    f"{error_message}"
                )

    if result.entry_score <= result.exit_score:
        raise RuntimeError(
            "Entry Score는 Exit Score보다 "
            "높아야 합니다."
        )

    if not (
        DEFAULT_MIN_STOP_ATR
        <= result.stop_atr_multiple
        <= DEFAULT_MAX_STOP_ATR
    ):
        raise RuntimeError(
            "Stop ATR이 허용 범위를 벗어났습니다."
        )

    if not (
        DEFAULT_MIN_TARGET_ATR
        <= result.target_atr_multiple
        <= DEFAULT_MAX_TARGET_ATR
    ):
        raise RuntimeError(
            "Target ATR이 허용 범위를 벗어났습니다."
        )

    if not (
        0
        < result.maximum_holding_days
        <= DEFAULT_MAX_HOLDING_DAYS
    ):
        raise RuntimeError(
            "Maximum Holding Days가 허용 범위를 "
            "벗어났습니다."
        )

    if not (
        0.0
        < result.position_percent
        <= DEFAULT_MAX_POSITION_PERCENT
    ):
        raise RuntimeError(
            "Position Percent가 허용 범위를 "
            "벗어났습니다."
        )


def validate_runtime_permissions(
    result: StrategyRuntimeGuardResult,
) -> None:
    """
    Runtime Mode별 권한 설정을 검사합니다.
    """

    expected_permissions = (
        calculate_expected_permissions(
            result.runtime_mode
        )
    )

    module_permissions = (
        evaluate_runtime_permissions(
            result.runtime_mode
        )
    )

    if module_permissions != expected_permissions:
        raise RuntimeError(
            "evaluate_runtime_permissions 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    actual_permissions = {
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
    }

    if actual_permissions != expected_permissions:
        raise RuntimeError(
            "Runtime Guard 권한이 Runtime Mode의 "
            "예상 권한과 일치하지 않습니다."
        )

    if (
        result.live_execution_blocked
        != (
            not result.live_execution_allowed
        )
    ):
        raise RuntimeError(
            "Live Execution Blocked 값이 "
            "Live Execution Allowed와 일치하지 않습니다."
        )

    if (
        result.paper_execution_blocked
        != (
            not result.paper_execution_allowed
        )
    ):
        raise RuntimeError(
            "Paper Execution Blocked 값이 "
            "Paper Execution Allowed와 일치하지 않습니다."
        )


def validate_check_consistency(
    result: StrategyRuntimeGuardResult,
) -> None:
    """
    Source, Parameter, Execution 및 전체 검사 값의
    내부 일관성을 확인합니다.
    """

    expected_all_checks = (
        result.source_checks_passed
        and result.parameter_checks_passed
        and result.execution_checks_passed
    )

    if (
        result.all_checks_passed
        != expected_all_checks
    ):
        raise RuntimeError(
            "All Checks Passed 값이 개별 검사 "
            "결과와 일치하지 않습니다."
        )

    expected_status = (
        calculate_expected_guard_status(
            runtime_mode=result.runtime_mode,
            all_checks_passed=(
                result.all_checks_passed
            ),
        )
    )

    module_status = determine_guard_status(
        runtime_mode=result.runtime_mode,
        all_checks_passed=(
            result.all_checks_passed
        ),
    )

    if module_status != expected_status:
        raise RuntimeError(
            "determine_guard_status 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.guard_status != expected_status:
        raise RuntimeError(
            "Guard Status가 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_status}, "
            f"Actual={result.guard_status}"
        )


def validate_execution_safety(
    result: StrategyRuntimeGuardResult,
) -> None:
    """
    실제 주문과 모의 주문의 안전 조건을 검사합니다.
    """

    if result.live_execution_allowed:
        if result.runtime_mode != "LIVE_READY":
            raise RuntimeError(
                "LIVE_READY가 아닌 상태에서 "
                "실거래가 허용되었습니다."
            )

        if (
            result.configuration_mode
            != "ACTIVE"
        ):
            raise RuntimeError(
                "ACTIVE Configuration이 아닌 상태에서 "
                "실거래가 허용되었습니다."
            )

        if (
            not result.execution_enabled_from_configuration
        ):
            raise RuntimeError(
                "Configuration의 Execution Enabled가 "
                "False인데 실거래가 허용되었습니다."
            )

        if result.manual_approval_required:
            raise RuntimeError(
                "수동 승인이 필요한 상태에서 "
                "실거래가 허용되었습니다."
            )

    if result.paper_execution_allowed:
        if result.runtime_mode not in {
            "LIVE_READY",
            "PAPER_READY",
        }:
            raise RuntimeError(
                "허용되지 않은 Runtime Mode에서 "
                "모의투자가 허용되었습니다."
            )

        if (
            result.runtime_mode == "PAPER_READY"
            and result.configuration_mode
            != "PAPER_TRADING"
        ):
            raise RuntimeError(
                "PAPER_TRADING Configuration이 아닌데 "
                "PAPER_READY가 설정되었습니다."
            )

    if result.runtime_mode == "ANALYSIS_ONLY":
        if result.live_execution_allowed:
            raise RuntimeError(
                "ANALYSIS_ONLY에서 실거래가 "
                "허용되었습니다."
            )

        if result.paper_execution_allowed:
            raise RuntimeError(
                "ANALYSIS_ONLY에서 모의투자가 "
                "허용되었습니다."
            )

        if not result.analysis_allowed:
            raise RuntimeError(
                "ANALYSIS_ONLY에서 분석 권한이 "
                "비활성화되었습니다."
            )

        if not result.backtest_allowed:
            raise RuntimeError(
                "ANALYSIS_ONLY에서 백테스트 권한이 "
                "비활성화되었습니다."
            )


def validate_current_baseline_result(
    result: StrategyRuntimeGuardResult,
) -> None:
    """
    현재 AAPL BASELINE Configuration에서
    예상되는 V8.8 결과를 검사합니다.
    """

    if result.configuration_mode != "BASELINE":
        return

    if result.runtime_mode != "ANALYSIS_ONLY":
        raise RuntimeError(
            "BASELINE Configuration인데 Runtime Mode가 "
            "ANALYSIS_ONLY가 아닙니다."
        )

    if (
        result.runtime_label
        != "기준 전략 분석 전용"
    ):
        raise RuntimeError(
            "BASELINE Runtime Label이 올바르지 않습니다."
        )

    if result.guard_status != "RESTRICTED":
        raise RuntimeError(
            "BASELINE의 Guard Status가 "
            "RESTRICTED가 아닙니다."
        )

    if not result.analysis_allowed:
        raise RuntimeError(
            "BASELINE에서 분석이 허용되지 않았습니다."
        )

    if not result.backtest_allowed:
        raise RuntimeError(
            "BASELINE에서 백테스트가 "
            "허용되지 않았습니다."
        )

    if not result.research_allowed:
        raise RuntimeError(
            "BASELINE에서 연구가 허용되지 않았습니다."
        )

    if result.paper_execution_allowed:
        raise RuntimeError(
            "BASELINE에서 모의투자가 허용되었습니다."
        )

    if result.live_execution_allowed:
        raise RuntimeError(
            "BASELINE에서 실거래가 허용되었습니다."
        )

    if not result.live_execution_blocked:
        raise RuntimeError(
            "BASELINE에서 Live Execution Blocked가 "
            "False입니다."
        )

    if not result.paper_execution_blocked:
        raise RuntimeError(
            "BASELINE에서 Paper Execution Blocked가 "
            "False입니다."
        )

    if not result.manual_approval_required:
        raise RuntimeError(
            "BASELINE에서 Manual Approval Required가 "
            "False입니다."
        )

    baseline_reason_exists = any(
        "기준 전략"
        in str(reason)
        for reason in result.reasons
    )

    if not baseline_reason_exists:
        raise RuntimeError(
            "Reasons에 기준 전략 관련 설명이 없습니다."
        )

    execution_block_reason_exists = any(
        (
            "실제 주문"
            in str(reason)
        )
        or (
            "모의 주문"
            in str(reason)
        )
        or (
            "차단"
            in str(reason)
        )
        for reason in result.blocking_reasons
    )

    if not execution_block_reason_exists:
        raise RuntimeError(
            "Blocking Reasons에 주문 실행 차단 "
            "설명이 없습니다."
        )


def validate_source_parameter_matches(
    result: StrategyRuntimeGuardResult,
    source_payload: dict[str, Any],
) -> None:
    """
    Runtime Guard 파라미터가 원본 V8.7
    Configuration과 일치하는지 검사합니다.
    """

    parameter_checks = {
        "entry_score": (
            result.entry_score,
            safe_float(
                source_payload.get(
                    "entry_score"
                )
            ),
        ),
        "exit_score": (
            result.exit_score,
            safe_float(
                source_payload.get(
                    "exit_score"
                )
            ),
        ),
        "stop_atr_multiple": (
            result.stop_atr_multiple,
            safe_float(
                source_payload.get(
                    "stop_atr_multiple"
                )
            ),
        ),
        "target_atr_multiple": (
            result.target_atr_multiple,
            safe_float(
                source_payload.get(
                    "target_atr_multiple"
                )
            ),
        ),
        "maximum_holding_days": (
            float(
                result.maximum_holding_days
            ),
            safe_float(
                source_payload.get(
                    "maximum_holding_days"
                )
            ),
        ),
        "position_percent": (
            result.position_percent,
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
                f"원본 Configuration의 {field_name} 값을 "
                "숫자로 변환할 수 없습니다."
            )

        if abs(
            float(actual_value)
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"{field_name} 값이 원본 Configuration과 "
                "일치하지 않습니다. "
                f"Expected={expected_value}, "
                f"Actual={actual_value}"
            )


def validate_saved_files(
    result: StrategyRuntimeGuardResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    저장된 V8.8 Runtime Guard JSON을 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            "시간별 Runtime Guard 보고서가 없습니다: "
            f"{report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            "Runtime Guard Latest 파일이 없습니다: "
            f"{latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 Runtime Guard 보고서가 비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "Runtime Guard Latest 파일이 비어 있습니다."
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "시간별 Runtime Guard 보고서와 "
            "Latest 파일의 내용이 일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_configuration_file",
        "configuration_mode",
        "configuration_ready",
        "runtime_mode",
        "runtime_label",
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
        "execution_enabled_from_configuration",
        "paper_execution_enabled_from_configuration",
        "manual_approval_required",
        "parameter_checks_passed",
        "execution_checks_passed",
        "source_checks_passed",
        "all_checks_passed",
        "live_execution_blocked",
        "paper_execution_blocked",
        "blocking_reasons",
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
            "저장된 V8.8 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    text_checks = {
        "version": result.version,
        "symbol": result.symbol,
        "source_configuration_file": (
            result.source_configuration_file
        ),
        "configuration_mode": (
            result.configuration_mode
        ),
        "runtime_mode": (
            result.runtime_mode
        ),
        "runtime_label": (
            result.runtime_label
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
        "configuration_ready": (
            result.configuration_ready
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
        "execution_enabled_from_configuration": (
            result.execution_enabled_from_configuration
        ),
        "paper_execution_enabled_from_configuration": (
            result.paper_execution_enabled_from_configuration
        ),
        "manual_approval_required": (
            result.manual_approval_required
        ),
        "parameter_checks_passed": (
            result.parameter_checks_passed
        ),
        "execution_checks_passed": (
            result.execution_checks_passed
        ),
        "source_checks_passed": (
            result.source_checks_passed
        ),
        "all_checks_passed": (
            result.all_checks_passed
        ),
        "live_execution_blocked": (
            result.live_execution_blocked
        ),
        "paper_execution_blocked": (
            result.paper_execution_blocked
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

    numeric_checks = {
        "entry_score": result.entry_score,
        "exit_score": result.exit_score,
        "stop_atr_multiple": (
            result.stop_atr_multiple
        ),
        "target_atr_multiple": (
            result.target_atr_multiple
        ),
        "maximum_holding_days": (
            float(
                result.maximum_holding_days
            )
        ),
        "position_percent": (
            result.position_percent
        ),
    }

    for field_name, expected_value in (
        numeric_checks.items()
    ):
        actual_value = safe_float(
            report_payload.get(
                field_name
            )
        )

        if actual_value is None:
            raise RuntimeError(
                f"저장된 {field_name} 값을 숫자로 "
                "변환할 수 없습니다."
            )

        if abs(
            actual_value
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    list_checks = {
        "blocking_reasons": (
            result.blocking_reasons
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
    result: StrategyRuntimeGuardResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.8 Runtime Guard 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V8.8 STRATEGY RUNTIME GUARD "
        "TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

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

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Configuration file      : "
        f"{result.source_configuration_file}"
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
    result: StrategyRuntimeGuardResult,
    source_payload: dict[str, Any],
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True/False로 출력합니다.
    """

    (
        expected_runtime_mode,
        expected_runtime_label,
    ) = calculate_expected_runtime_mode(
        configuration_mode=(
            result.configuration_mode
        ),
        configuration_ready=(
            result.configuration_ready
        ),
        execution_enabled=(
            result.execution_enabled_from_configuration
        ),
        paper_execution_enabled=(
            result.paper_execution_enabled_from_configuration
        ),
        manual_approval_required=(
            result.manual_approval_required
        ),
    )

    expected_permissions = (
        calculate_expected_permissions(
            result.runtime_mode
        )
    )

    expected_all_checks = (
        result.source_checks_passed
        and result.parameter_checks_passed
        and result.execution_checks_passed
    )

    expected_guard_status = (
        calculate_expected_guard_status(
            runtime_mode=result.runtime_mode,
            all_checks_passed=(
                result.all_checks_passed
            ),
        )
    )

    source_path = Path(
        result.source_configuration_file
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

    source_mode_matches = (
        str(
            source_payload.get(
                "configuration_mode",
                "",
            )
        ).upper()
        == result.configuration_mode
    )

    print()
    print("=" * 140)
    print("VALIDATION CHECKS")
    print("=" * 140)

    print(
        f"Version is V8.8                   : "
        f"{result.version == 'V8.8'}"
    )

    print(
        f"Configuration mode is valid       : "
        f"{(
            result.configuration_mode
            in VALID_CONFIGURATION_MODES
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
        f"Source Configuration exists       : "
        f"{source_path.exists()}"
    )

    print(
        f"Source Symbol matches             : "
        f"{source_symbol_matches}"
    )

    print(
        f"Source mode matches               : "
        f"{source_mode_matches}"
    )

    print(
        f"Runtime mode matches              : "
        f"{result.runtime_mode == expected_runtime_mode}"
    )

    print(
        f"Runtime label matches             : "
        f"{result.runtime_label == expected_runtime_label}"
    )

    print(
        f"Parameter checks passed           : "
        f"{result.parameter_checks_passed}"
    )

    print(
        f"Source checks passed              : "
        f"{result.source_checks_passed}"
    )

    print(
        f"Execution checks passed           : "
        f"{result.execution_checks_passed}"
    )

    print(
        f"All checks match                  : "
        f"{result.all_checks_passed == expected_all_checks}"
    )

    print(
        f"Guard status matches              : "
        f"{result.guard_status == expected_guard_status}"
    )

    print(
        f"Analysis permission matches       : "
        f"{(
            result.analysis_allowed
            == expected_permissions[
                'analysis_allowed'
            ]
        )}"
    )

    print(
        f"Backtest permission matches       : "
        f"{(
            result.backtest_allowed
            == expected_permissions[
                'backtest_allowed'
            ]
        )}"
    )

    print(
        f"Research permission matches       : "
        f"{(
            result.research_allowed
            == expected_permissions[
                'research_allowed'
            ]
        )}"
    )

    print(
        f"Paper permission matches          : "
        f"{(
            result.paper_execution_allowed
            == expected_permissions[
                'paper_execution_allowed'
            ]
        )}"
    )

    print(
        f"Live permission matches           : "
        f"{(
            result.live_execution_allowed
            == expected_permissions[
                'live_execution_allowed'
            ]
        )}"
    )

    print(
        f"Live block flag matches           : "
        f"{(
            result.live_execution_blocked
            == (
                not result.live_execution_allowed
            )
        )}"
    )

    print(
        f"Paper block flag matches          : "
        f"{(
            result.paper_execution_blocked
            == (
                not result.paper_execution_allowed
            )
        )}"
    )

    print(
        f"Entry is above Exit               : "
        f"{result.entry_score > result.exit_score}"
    )

    print(
        f"Stop ATR is safe                  : "
        f"{(
            DEFAULT_MIN_STOP_ATR
            <= result.stop_atr_multiple
            <= DEFAULT_MAX_STOP_ATR
        )}"
    )

    print(
        f"Target ATR is safe                : "
        f"{(
            DEFAULT_MIN_TARGET_ATR
            <= result.target_atr_multiple
            <= DEFAULT_MAX_TARGET_ATR
        )}"
    )

    print(
        f"Holding days are safe             : "
        f"{(
            0
            < result.maximum_holding_days
            <= DEFAULT_MAX_HOLDING_DAYS
        )}"
    )

    print(
        f"Position percent is safe          : "
        f"{(
            0.0
            < result.position_percent
            <= DEFAULT_MAX_POSITION_PERCENT
        )}"
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
    V8.8 Strategy Runtime Guard 통합 테스트입니다.

    검사 항목:

    1. V8.7 Configuration Latest 파일 로딩
    2. 원본 파일 버전 및 Symbol 확인
    3. Runtime Mode 변환 확인
    4. 전략 파라미터 안전 범위 검사
    5. 분석 및 백테스트 권한 검사
    6. 모의투자 권한 검사
    7. 실거래 권한 검사
    8. 수동 승인 조건 검사
    9. Guard Status 계산 검사
    10. Runtime Guard JSON 저장 및 검증
    """

    symbol = "AAPL"

    print_test_header()

    try:
        result = run_strategy_runtime_guard(
            symbol=symbol,
        )

        (
            report_path,
            latest_path,
        ) = save_strategy_runtime_guard(
            result
        )

        # 저장 경로가 결과 객체에 반영된 후
        # 전체 Runtime Guard를 다시 출력합니다.
        print_strategy_runtime_guard(
            result
        )

        validate_result_structure(
            result
        )

        source_payload = validate_source_configuration(
            result
        )

        validate_runtime_mode(
            result
        )

        validate_runtime_parameters_result(
            result
        )

        validate_runtime_permissions(
            result
        )

        validate_check_consistency(
            result
        )

        validate_execution_safety(
            result
        )

        validate_current_baseline_result(
            result
        )

        validate_source_parameter_matches(
            result=result,
            source_payload=source_payload,
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
            "V8.8 strategy runtime guard "
            "test completed successfully."
        )

        if result.runtime_mode == "ANALYSIS_ONLY":
            print(
                "현재 전략은 분석과 백테스트에만 "
                "사용되며 주문 실행은 정상 차단되었습니다."
            )

        elif result.runtime_mode == "PAPER_READY":
            print(
                "모의투자 실행 조건은 통과했지만 "
                "실거래 실행은 정상 차단되었습니다."
            )

        elif result.runtime_mode == "LIVE_READY":
            print(
                "실거래 준비 조건을 통과했습니다. "
                "실제 주문 연결 전 별도의 최종 승인이 필요합니다."
            )

        elif result.runtime_mode == "RESEARCH_ONLY":
            print(
                "현재 전략은 연구와 백테스트 전용으로 "
                "정상 제한되었습니다."
            )

        else:
            print(
                "현재 Configuration을 이용한 모든 실행이 "
                "정상 차단되었습니다."
            )

        print(
            "주의: 이 Runtime Guard는 실행 권한만 "
            "판정하며 실제 증권 주문이나 자동 매매를 "
            "실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V8.8 Strategy Runtime Guard "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V8.8 STRATEGY RUNTIME GUARD ERROR"
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