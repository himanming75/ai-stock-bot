import json
from pathlib import Path
from typing import Any

from backtest.strategy_configuration_loader import (
    DEFAULT_BASELINE_PARAMETERS,
    VALID_CONFIGURATION_MODES,
    VALID_REGISTRY_MODES,
    StrategyConfiguration,
    determine_configuration_mode,
    print_strategy_configuration,
    run_strategy_configuration_loader,
    save_strategy_configuration,
    validate_parameters,
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


VALID_CONFIDENCE_LEVELS = {
    "HIGH",
    "MEDIUM",
    "LOW",
    "UNKNOWN",
}


VALID_RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "UNKNOWN",
}


def print_test_header() -> None:
    """
    V8.7 Strategy Configuration Loader
    테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V8.7 "
        "STRATEGY CONFIGURATION LOADER TEST"
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


def calculate_expected_configuration_mode(
    registry_mode: str,
) -> tuple[str, str]:
    """
    Registry Mode에 따라 예상되는
    Configuration Mode와 Label을 계산합니다.
    """

    normalized_mode = (
        registry_mode
        .strip()
        .upper()
    )

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


def validate_result_structure(
    result: StrategyConfiguration,
) -> None:
    """
    V8.7 Configuration 결과의
    기본 구조와 자료형을 검사합니다.
    """

    if result.version != "V8.7":
        raise RuntimeError(
            "Configuration 버전이 V8.7이 아닙니다: "
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

    if not result.source_registry_file:
        raise RuntimeError(
            "Source Registry File이 비어 있습니다."
        )

    if (
        result.registry_mode
        not in VALID_REGISTRY_MODES
    ):
        raise RuntimeError(
            "올바르지 않은 Registry Mode입니다: "
            f"{result.registry_mode}"
        )

    if (
        result.configuration_mode
        not in VALID_CONFIGURATION_MODES
    ):
        raise RuntimeError(
            "올바르지 않은 Configuration Mode입니다: "
            f"{result.configuration_mode}"
        )

    if not result.configuration_label:
        raise RuntimeError(
            "Configuration Label이 비어 있습니다."
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
        "Registry Ready": (
            result.registry_ready
        ),
        "Configuration Ready": (
            result.configuration_ready
        ),
        "Execution Enabled": (
            result.execution_enabled
        ),
        "Paper Execution Enabled": (
            result.paper_execution_enabled
        ),
        "Manual Approval Required": (
            result.manual_approval_required
        ),
        "Default Configuration": (
            result.is_default_configuration
        ),
        "Fallback Used": (
            result.fallback_used
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

    if not isinstance(
        result.entry_score,
        float,
    ):
        raise RuntimeError(
            "Entry Score가 float 형식이 아닙니다."
        )

    if not isinstance(
        result.exit_score,
        float,
    ):
        raise RuntimeError(
            "Exit Score가 float 형식이 아닙니다."
        )

    if not isinstance(
        result.stop_atr_multiple,
        float,
    ):
        raise RuntimeError(
            "Stop ATR Multiple이 float 형식이 아닙니다."
        )

    if not isinstance(
        result.target_atr_multiple,
        float,
    ):
        raise RuntimeError(
            "Target ATR Multiple이 float 형식이 아닙니다."
        )

    if not isinstance(
        result.maximum_holding_days,
        int,
    ):
        raise RuntimeError(
            "Maximum Holding Days가 int 형식이 아닙니다."
        )

    if not isinstance(
        result.position_percent,
        float,
    ):
        raise RuntimeError(
            "Position Percent가 float 형식이 아닙니다."
        )

    optional_score_fields = {
        "Candidate Score": (
            result.candidate_score
        ),
        "Baseline Score": (
            result.baseline_score
        ),
        "Confidence Score": (
            result.confidence_score
        ),
        "Risk Score": (
            result.risk_score
        ),
    }

    for field_name, value in (
        optional_score_fields.items()
    ):
        if value is None:
            continue

        if not 0.0 <= value <= 100.0:
            raise RuntimeError(
                f"{field_name}가 0~100 범위를 "
                f"벗어났습니다: {value}"
            )

    if (
        result.confidence_level
        not in VALID_CONFIDENCE_LEVELS
    ):
        raise RuntimeError(
            "올바르지 않은 Confidence Level입니다: "
            f"{result.confidence_level}"
        )

    if (
        result.risk_level
        not in VALID_RISK_LEVELS
    ):
        raise RuntimeError(
            "올바르지 않은 Risk Level입니다: "
            f"{result.risk_level}"
        )

    if result.recommendation_strength is not None:
        if not 1 <= result.recommendation_strength <= 5:
            raise RuntimeError(
                "Recommendation Strength가 "
                "1~5 범위를 벗어났습니다: "
                f"{result.recommendation_strength}"
            )

    list_fields = {
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


def validate_source_registry(
    result: StrategyConfiguration,
) -> dict[str, Any]:
    """
    V8.6 Registry 원본 파일과
    V8.7 Configuration 결과를 비교합니다.
    """

    source_path = Path(
        result.source_registry_file
    )

    if not source_path.exists():
        raise RuntimeError(
            "Source Registry 파일이 존재하지 않습니다: "
            f"{source_path}"
        )

    if source_path.stat().st_size <= 0:
        raise RuntimeError(
            "Source Registry 파일이 비어 있습니다."
        )

    source_payload = load_json_file(
        source_path
    )

    if (
        str(
            source_payload.get(
                "version",
                "",
            )
        ).upper()
        != "V8.6"
    ):
        raise RuntimeError(
            "Source Registry 파일의 버전이 "
            "V8.6이 아닙니다."
        )

    source_symbol = str(
        source_payload.get(
            "symbol",
            "",
        )
    ).upper()

    if source_symbol != result.symbol:
        raise RuntimeError(
            "Source Registry의 Symbol과 "
            "Configuration Symbol이 일치하지 않습니다."
        )

    source_registry_mode = str(
        source_payload.get(
            "registry_mode",
            "",
        )
    ).upper()

    if (
        source_registry_mode
        != result.registry_mode
    ):
        raise RuntimeError(
            "Source Registry Mode와 Configuration의 "
            "Registry Mode가 일치하지 않습니다."
        )

    source_strategy_source = str(
        source_payload.get(
            "selected_strategy_source",
            "NONE",
        )
    )

    if (
        source_strategy_source
        != result.strategy_source
    ):
        raise RuntimeError(
            "Strategy Source가 Source Registry와 "
            "일치하지 않습니다."
        )

    source_strategy_status = str(
        source_payload.get(
            "selected_strategy_status",
            "UNREGISTERED",
        )
    )

    if (
        source_strategy_status
        != result.strategy_status
    ):
        raise RuntimeError(
            "Strategy Status가 Source Registry와 "
            "일치하지 않습니다."
        )

    return source_payload


def validate_configuration_mode(
    result: StrategyConfiguration,
) -> None:
    """
    Registry Mode에서 Configuration Mode로
    정상 변환되었는지 검사합니다.
    """

    (
        expected_mode,
        expected_label,
    ) = calculate_expected_configuration_mode(
        result.registry_mode
    )

    module_mode = determine_configuration_mode(
        result.registry_mode
    )

    if module_mode != (
        expected_mode,
        expected_label,
    ):
        raise RuntimeError(
            "determine_configuration_mode 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if (
        result.configuration_mode
        != expected_mode
    ):
        raise RuntimeError(
            "Configuration Mode가 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_mode}, "
            f"Actual={result.configuration_mode}"
        )

    if (
        result.configuration_label
        != expected_label
    ):
        raise RuntimeError(
            "Configuration Label이 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_label}, "
            f"Actual={result.configuration_label}"
        )


def validate_configuration_parameters(
    result: StrategyConfiguration,
) -> None:
    """
    설정 파라미터 범위와 관계를 검사합니다.
    """

    validate_parameters(
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

    if result.entry_score <= result.exit_score:
        raise RuntimeError(
            "Entry Score는 Exit Score보다 "
            "높아야 합니다."
        )

    if result.stop_atr_multiple <= 0.0:
        raise RuntimeError(
            "Stop ATR Multiple이 0 이하입니다."
        )

    if result.target_atr_multiple <= 0.0:
        raise RuntimeError(
            "Target ATR Multiple이 0 이하입니다."
        )

    if result.maximum_holding_days <= 0:
        raise RuntimeError(
            "Maximum Holding Days가 0 이하입니다."
        )

    if not 0.0 < result.position_percent <= 100.0:
        raise RuntimeError(
            "Position Percent가 올바르지 않습니다."
        )


def validate_parameter_source(
    result: StrategyConfiguration,
    source_payload: dict[str, Any],
) -> None:
    """
    Registry에 유효한 파라미터가 있으면 그대로 사용하고,
    값이 없으면 기본값을 사용했는지 검사합니다.
    """

    parameter_fields = {
        "entry_score": (
            result.entry_score,
            DEFAULT_BASELINE_PARAMETERS[
                "entry_score"
            ],
            float,
        ),
        "exit_score": (
            result.exit_score,
            DEFAULT_BASELINE_PARAMETERS[
                "exit_score"
            ],
            float,
        ),
        "stop_atr_multiple": (
            result.stop_atr_multiple,
            DEFAULT_BASELINE_PARAMETERS[
                "stop_atr_multiple"
            ],
            float,
        ),
        "target_atr_multiple": (
            result.target_atr_multiple,
            DEFAULT_BASELINE_PARAMETERS[
                "target_atr_multiple"
            ],
            float,
        ),
        "maximum_holding_days": (
            result.maximum_holding_days,
            DEFAULT_BASELINE_PARAMETERS[
                "maximum_holding_days"
            ],
            int,
        ),
        "position_percent": (
            result.position_percent,
            DEFAULT_BASELINE_PARAMETERS[
                "position_percent"
            ],
            float,
        ),
    }

    fallback_expected = False

    for field_name, (
        actual_value,
        default_value,
        expected_type,
    ) in parameter_fields.items():
        source_value = source_payload.get(
            field_name
        )

        if expected_type is int:
            converted_source = safe_int(
                source_value
            )
        else:
            converted_source = safe_float(
                source_value
            )

        if converted_source is None:
            fallback_expected = True
            expected_value = default_value
        else:
            expected_value = converted_source

        if abs(
            float(actual_value)
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"{field_name} 값이 Registry 또는 "
                "기본값과 일치하지 않습니다. "
                f"Expected={expected_value}, "
                f"Actual={actual_value}"
            )

    if (
        result.fallback_used
        != fallback_expected
    ):
        raise RuntimeError(
            "Fallback Used 값이 실제 기본값 사용 여부와 "
            "일치하지 않습니다."
        )


def validate_evaluation_consistency(
    result: StrategyConfiguration,
) -> None:
    """
    후보 점수, 기준 점수 및 개선 점수의
    내부 일관성을 검사합니다.
    """

    if (
        result.candidate_score is not None
        and result.baseline_score is not None
        and result.score_improvement is not None
    ):
        expected_improvement = round(
            result.candidate_score
            - result.baseline_score,
            2,
        )

        if abs(
            expected_improvement
            - result.score_improvement
        ) > 0.01:
            raise RuntimeError(
                "Score Improvement 계산이 "
                "일치하지 않습니다. "
                f"Expected={expected_improvement:+.2f}, "
                f"Actual={result.score_improvement:+.2f}"
            )

    if (
        result.configuration_mode == "BASELINE"
        and result.score_improvement is not None
        and result.score_improvement > 0.0
    ):
        raise RuntimeError(
            "BASELINE 설정인데 후보 전략 점수가 "
            "기준 전략보다 높게 기록되어 있습니다."
        )


def validate_safety_settings(
    result: StrategyConfiguration,
) -> None:
    """
    실행 관련 안전 설정을 검사합니다.
    """

    if result.execution_enabled:
        raise RuntimeError(
            "Execution Enabled가 True입니다. "
            "V8.7 Loader에서는 실제 주문 실행이 "
            "비활성화되어야 합니다."
        )

    if not result.manual_approval_required:
        raise RuntimeError(
            "Manual Approval Required가 False입니다."
        )

    expected_configuration_ready = (
        result.registry_ready
        and result.configuration_mode
        != "UNAVAILABLE"
    )

    if (
        result.configuration_ready
        != expected_configuration_ready
    ):
        raise RuntimeError(
            "Configuration Ready 계산이 "
            "Registry 상태와 일치하지 않습니다."
        )

    expected_paper_execution = (
        result.configuration_mode
        == "PAPER_TRADING"
        and result.configuration_ready
    )

    if (
        result.paper_execution_enabled
        != expected_paper_execution
    ):
        raise RuntimeError(
            "Paper Execution Enabled 계산이 "
            "Configuration Mode와 일치하지 않습니다."
        )

    if (
        result.configuration_mode
        != "PAPER_TRADING"
        and result.paper_execution_enabled
    ):
        raise RuntimeError(
            "PAPER_TRADING이 아닌 설정에서 "
            "Paper Execution이 활성화되어 있습니다."
        )


def validate_current_baseline_result(
    result: StrategyConfiguration,
) -> None:
    """
    현재 AAPL의 V8.6 Registry가 BASELINE인 경우
    예상되는 V8.7 결과를 검사합니다.
    """

    if result.registry_mode != "BASELINE":
        return

    if result.configuration_mode != "BASELINE":
        raise RuntimeError(
            "Registry Mode가 BASELINE인데 "
            "Configuration Mode가 BASELINE이 아닙니다."
        )

    if (
        result.configuration_label
        != "기준 전략 설정"
    ):
        raise RuntimeError(
            "BASELINE Configuration Label이 "
            "올바르지 않습니다."
        )

    if not result.configuration_ready:
        raise RuntimeError(
            "BASELINE 설정이 준비되지 않은 상태입니다."
        )

    if not result.is_default_configuration:
        raise RuntimeError(
            "BASELINE 설정인데 "
            "Default Configuration이 False입니다."
        )

    if result.paper_execution_enabled:
        raise RuntimeError(
            "BASELINE 설정에서 Paper Execution이 "
            "활성화되어 있습니다."
        )

    if result.execution_enabled:
        raise RuntimeError(
            "BASELINE 설정에서 실제 실행이 "
            "활성화되어 있습니다."
        )

    baseline_reason_exists = any(
        (
            "기준 전략"
            in str(reason)
        )
        for reason in result.reasons
    )

    if not baseline_reason_exists:
        raise RuntimeError(
            "Reasons에 기준 전략 유지 설명이 없습니다."
        )


def validate_saved_files(
    result: StrategyConfiguration,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    저장된 V8.7 Configuration JSON 파일을 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            "시간별 Configuration 보고서가 없습니다: "
            f"{report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            "Configuration Latest 파일이 없습니다: "
            f"{latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 Configuration 보고서가 비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "Configuration Latest 파일이 비어 있습니다."
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "시간별 Configuration 보고서와 "
            "Latest 파일의 내용이 일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_registry_file",
        "registry_mode",
        "configuration_mode",
        "configuration_label",
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
        "candidate_score",
        "baseline_score",
        "score_improvement",
        "confidence_score",
        "confidence_level",
        "risk_score",
        "risk_level",
        "recommendation_strength",
        "registry_ready",
        "configuration_ready",
        "execution_enabled",
        "paper_execution_enabled",
        "manual_approval_required",
        "is_default_configuration",
        "fallback_used",
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
            "저장된 V8.7 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    text_value_checks = {
        "version": result.version,
        "symbol": result.symbol,
        "source_registry_file": (
            result.source_registry_file
        ),
        "registry_mode": (
            result.registry_mode
        ),
        "configuration_mode": (
            result.configuration_mode
        ),
        "configuration_label": (
            result.configuration_label
        ),
        "strategy_source": (
            result.strategy_source
        ),
        "strategy_status": (
            result.strategy_status
        ),
        "confidence_level": (
            result.confidence_level
        ),
        "risk_level": (
            result.risk_level
        ),
    }

    for field_name, expected_value in (
        text_value_checks.items()
    ):
        if (
            str(
                report_payload.get(
                    field_name
                )
            )
            != str(expected_value)
        ):
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    boolean_value_checks = {
        "registry_ready": (
            result.registry_ready
        ),
        "configuration_ready": (
            result.configuration_ready
        ),
        "execution_enabled": (
            result.execution_enabled
        ),
        "paper_execution_enabled": (
            result.paper_execution_enabled
        ),
        "manual_approval_required": (
            result.manual_approval_required
        ),
        "is_default_configuration": (
            result.is_default_configuration
        ),
        "fallback_used": (
            result.fallback_used
        ),
    }

    for field_name, expected_value in (
        boolean_value_checks.items()
    ):
        if (
            bool(
                report_payload.get(
                    field_name
                )
            )
            != expected_value
        ):
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    numeric_value_checks = {
        "entry_score": result.entry_score,
        "exit_score": result.exit_score,
        "stop_atr_multiple": (
            result.stop_atr_multiple
        ),
        "target_atr_multiple": (
            result.target_atr_multiple
        ),
        "maximum_holding_days": (
            result.maximum_holding_days
        ),
        "position_percent": (
            result.position_percent
        ),
    }

    for field_name, expected_value in (
        numeric_value_checks.items()
    ):
        actual_value = safe_float(
            report_payload.get(
                field_name
            )
        )

        if actual_value is None:
            raise RuntimeError(
                f"저장된 {field_name} 값을 "
                "숫자로 변환할 수 없습니다."
            )

        if abs(
            actual_value
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    optional_numeric_checks = {
        "candidate_score": (
            result.candidate_score
        ),
        "baseline_score": (
            result.baseline_score
        ),
        "score_improvement": (
            result.score_improvement
        ),
        "confidence_score": (
            result.confidence_score
        ),
        "risk_score": (
            result.risk_score
        ),
        "recommendation_strength": (
            result.recommendation_strength
        ),
    }

    for field_name, expected_value in (
        optional_numeric_checks.items()
    ):
        actual_value = report_payload.get(
            field_name
        )

        if expected_value is None:
            if actual_value is not None:
                raise RuntimeError(
                    f"저장된 {field_name} 값은 "
                    "None이어야 합니다."
                )

            continue

        converted_value = safe_float(
            actual_value
        )

        if converted_value is None:
            raise RuntimeError(
                f"저장된 {field_name} 값을 "
                "숫자로 변환할 수 없습니다."
            )

        if abs(
            converted_value
            - float(expected_value)
        ) > 0.01:
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
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
    result: StrategyConfiguration,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.7 Configuration 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V8.7 STRATEGY CONFIGURATION "
        "LOADER TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

    print(
        f"Registry mode                  : "
        f"{result.registry_mode}"
    )

    print(
        f"Configuration mode             : "
        f"{result.configuration_mode}"
    )

    print(
        f"Configuration label            : "
        f"{result.configuration_label}"
    )

    print(
        f"Registry ready                 : "
        f"{result.registry_ready}"
    )

    print(
        f"Configuration ready            : "
        f"{result.configuration_ready}"
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
    print("EVALUATION")
    print("-" * 140)

    print(
        f"Candidate score                : "
        f"{result.candidate_score}"
    )

    print(
        f"Baseline score                 : "
        f"{result.baseline_score}"
    )

    if result.score_improvement is None:
        improvement_text = "None"
    else:
        improvement_text = (
            f"{result.score_improvement:+.2f} points"
        )

    print(
        f"Score improvement              : "
        f"{improvement_text}"
    )

    print(
        f"Confidence                     : "
        f"{result.confidence_score}/100 "
        f"({result.confidence_level})"
    )

    print(
        f"Risk                           : "
        f"{result.risk_score}/100 "
        f"({result.risk_level})"
    )

    print(
        f"Recommendation strength        : "
        f"{result.recommendation_strength}/5"
    )

    print()
    print("SAFETY")
    print("-" * 140)

    print(
        f"Execution enabled              : "
        f"{result.execution_enabled}"
    )

    print(
        f"Paper execution enabled        : "
        f"{result.paper_execution_enabled}"
    )

    print(
        f"Manual approval required       : "
        f"{result.manual_approval_required}"
    )

    print(
        f"Default configuration          : "
        f"{result.is_default_configuration}"
    )

    print(
        f"Fallback used                  : "
        f"{result.fallback_used}"
    )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Registry file           : "
        f"{result.source_registry_file}"
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
    result: StrategyConfiguration,
    source_payload: dict[str, Any],
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True/False로 출력합니다.
    """

    (
        expected_mode,
        expected_label,
    ) = calculate_expected_configuration_mode(
        result.registry_mode
    )

    expected_ready = (
        result.registry_ready
        and result.configuration_mode
        != "UNAVAILABLE"
    )

    expected_paper_execution = (
        result.configuration_mode
        == "PAPER_TRADING"
        and result.configuration_ready
    )

    score_improvement_matches = True

    if (
        result.candidate_score is not None
        and result.baseline_score is not None
        and result.score_improvement is not None
    ):
        score_improvement_matches = (
            abs(
                (
                    result.candidate_score
                    - result.baseline_score
                )
                - result.score_improvement
            )
            <= 0.01
        )

    source_file_exists = Path(
        result.source_registry_file
    ).exists()

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
                "registry_mode",
                "",
            )
        ).upper()
        == result.registry_mode
    )

    print()
    print("=" * 140)
    print("VALIDATION CHECKS")
    print("=" * 140)

    print(
        f"Version is V8.7                   : "
        f"{result.version == 'V8.7'}"
    )

    print(
        f"Registry mode is valid            : "
        f"{result.registry_mode in VALID_REGISTRY_MODES}"
    )

    print(
        f"Configuration mode is valid       : "
        f"{(
            result.configuration_mode
            in VALID_CONFIGURATION_MODES
        )}"
    )

    print(
        f"Configuration mode matches        : "
        f"{result.configuration_mode == expected_mode}"
    )

    print(
        f"Configuration label matches       : "
        f"{result.configuration_label == expected_label}"
    )

    print(
        f"Strategy source is valid          : "
        f"{result.strategy_source in VALID_STRATEGY_SOURCES}"
    )

    print(
        f"Strategy status is valid          : "
        f"{result.strategy_status in VALID_STRATEGY_STATUSES}"
    )

    print(
        f"Source Registry exists            : "
        f"{source_file_exists}"
    )

    print(
        f"Source Symbol matches             : "
        f"{source_symbol_matches}"
    )

    print(
        f"Source Registry mode matches      : "
        f"{source_mode_matches}"
    )

    print(
        f"Entry is above Exit               : "
        f"{result.entry_score > result.exit_score}"
    )

    print(
        f"Stop ATR is valid                 : "
        f"{result.stop_atr_multiple > 0.0}"
    )

    print(
        f"Target ATR is valid               : "
        f"{result.target_atr_multiple > 0.0}"
    )

    print(
        f"Holding days are valid            : "
        f"{result.maximum_holding_days > 0}"
    )

    print(
        f"Position percent is valid         : "
        f"{0.0 < result.position_percent <= 100.0}"
    )

    print(
        f"Score improvement matches         : "
        f"{score_improvement_matches}"
    )

    print(
        f"Configuration ready matches       : "
        f"{result.configuration_ready == expected_ready}"
    )

    print(
        f"Execution disabled                : "
        f"{not result.execution_enabled}"
    )

    print(
        f"Paper execution matches mode      : "
        f"{(
            result.paper_execution_enabled
            == expected_paper_execution
        )}"
    )

    print(
        f"Manual approval required          : "
        f"{result.manual_approval_required}"
    )

    print(
        f"Default flag matches mode         : "
        f"{(
            result.is_default_configuration
            == (
                result.configuration_mode
                == 'BASELINE'
            )
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
    V8.7 Strategy Configuration Loader
    통합 테스트입니다.

    검사 항목:

    1. V8.6 Registry Latest 파일 로딩
    2. Registry 구조와 Symbol 확인
    3. Configuration Mode 변환
    4. 전략 파라미터 변환
    5. 누락 파라미터 기본값 처리
    6. 점수 데이터 일관성
    7. 실제 주문 실행 비활성화
    8. 모의투자 실행 조건 확인
    9. Configuration JSON 저장
    10. 저장 파일 내용 검증
    """

    symbol = "AAPL"

    print_test_header()

    try:
        result = run_strategy_configuration_loader(
            symbol=symbol,
        )

        (
            report_path,
            latest_path,
        ) = save_strategy_configuration(
            result
        )

        # 저장 경로가 결과 객체에 반영된 후
        # 전체 Configuration을 다시 출력합니다.
        print_strategy_configuration(
            result
        )

        validate_result_structure(
            result
        )

        source_payload = validate_source_registry(
            result
        )

        validate_configuration_mode(
            result
        )

        validate_configuration_parameters(
            result
        )

        validate_parameter_source(
            result=result,
            source_payload=source_payload,
        )

        validate_evaluation_consistency(
            result
        )

        validate_safety_settings(
            result
        )

        validate_current_baseline_result(
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
            "V8.7 strategy configuration loader "
            "test completed successfully."
        )

        if (
            result.configuration_mode
            == "BASELINE"
        ):
            print(
                "V8.6 Registry의 기준 전략을 "
                "표준 Configuration으로 정상 변환했습니다."
            )

        elif (
            result.configuration_mode
            == "ACTIVE"
        ):
            print(
                "운영 전략을 표준 Configuration으로 "
                "정상 변환했습니다."
            )

        elif (
            result.configuration_mode
            == "PAPER_TRADING"
        ):
            print(
                "모의투자 전략을 표준 Configuration으로 "
                "정상 변환했습니다."
            )

        elif (
            result.configuration_mode
            == "RESEARCH_ONLY"
        ):
            print(
                "연구 전용 전략을 표준 Configuration으로 "
                "정상 변환했습니다."
            )

        else:
            print(
                "현재 사용할 수 있는 전략이 없는 상태를 "
                "정상 확인했습니다."
            )

        print(
            "주의: 이 Loader는 전략 설정만 제공하며 "
            "실제 증권 주문이나 자동 매매를 실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V8.7 Strategy Configuration "
            "Loader 테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V8.7 STRATEGY CONFIGURATION "
            "LOADER ERROR"
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