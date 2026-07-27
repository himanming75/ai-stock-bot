import json
from pathlib import Path
from typing import Any

from backtest.active_strategy_registry import (
    ActiveStrategyRegistryResult,
    VALID_PROMOTION_STATUSES,
    VALID_REGISTRY_MODES,
    determine_registry_mode,
    print_active_strategy_registry,
    run_active_strategy_registry,
    save_active_strategy_registry,
)


VALID_SELECTED_STRATEGY_STATUSES = {
    "ACTIVE",
    "PAPER_TRADING",
    "BASELINE_RETAINED",
    "BASELINE",
    "RESEARCH_ONLY",
    "UNREGISTERED",
}

VALID_SELECTED_STRATEGY_SOURCES = {
    "ACTIVE_STRATEGY",
    "PAPER_STRATEGY",
    "PROMOTION_BASELINE",
    "BASELINE_DEFAULT",
    "RESEARCH_ARCHIVE",
    "NONE",
}

VALID_CONFIDENCE_LEVELS = {
    "HIGH",
    "MEDIUM",
    "LOW",
    "UNKNOWN",
    None,
}

VALID_RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "UNKNOWN",
    None,
}


def print_test_header() -> None:
    """
    V8.6 Active Strategy Registry
    테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V8.6 "
        "ACTIVE STRATEGY REGISTRY TEST"
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


def calculate_expected_registry_mode(
    result: ActiveStrategyRegistryResult,
) -> tuple[str, str]:
    """
    현재 파일 상태와 최근 승격 결과를 바탕으로
    예상 Registry Mode를 독립적으로 계산합니다.
    """

    promotion_status = (
        result.promotion_status
        .strip()
        .upper()
    )

    if (
        result.active_strategy_exists
        and promotion_status == "PROMOTED"
    ):
        return (
            "ACTIVE",
            "운영 전략 등록",
        )

    if (
        result.paper_strategy_exists
        and promotion_status == "PAPER_TRADING"
    ):
        return (
            "PAPER_TRADING",
            "모의투자 전략 등록",
        )

    if promotion_status == "BASELINE_RETAINED":
        return (
            "BASELINE",
            "기존 기준 전략 유지",
        )

    if (
        promotion_status == "RESEARCH_ARCHIVED"
        or result.research_candidates_exist
    ):
        return (
            "RESEARCH_ONLY",
            "연구 후보만 등록",
        )

    if result.active_strategy_exists:
        return (
            "ACTIVE",
            "운영 전략 등록",
        )

    if result.paper_strategy_exists:
        return (
            "PAPER_TRADING",
            "모의투자 전략 등록",
        )

    return (
        "UNREGISTERED",
        "등록된 전략 없음",
    )


def validate_result_structure(
    result: ActiveStrategyRegistryResult,
) -> None:
    """
    V8.6 Registry 결과의 구조와 값 범위를 검사합니다.
    """

    if result.version != "V8.6":
        raise RuntimeError(
            f"보고서 버전이 V8.6이 아닙니다: "
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

    if result.registry_mode not in VALID_REGISTRY_MODES:
        raise RuntimeError(
            "올바르지 않은 Registry Mode입니다: "
            f"{result.registry_mode}"
        )

    if not result.registry_label:
        raise RuntimeError(
            "Registry Label이 비어 있습니다."
        )

    boolean_fields = {
        "Active Strategy Exists": (
            result.active_strategy_exists
        ),
        "Paper Strategy Exists": (
            result.paper_strategy_exists
        ),
        "Promotion Result Exists": (
            result.promotion_result_exists
        ),
        "Research Candidates Exist": (
            result.research_candidates_exist
        ),
        "Registry Ready": (
            result.registry_ready
        ),
        "Execution Enabled": (
            result.execution_enabled
        ),
        "Manual Approval Required": (
            result.manual_approval_required
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(
            value,
            bool,
        ):
            raise RuntimeError(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if result.research_candidate_count < 0:
        raise RuntimeError(
            "Research Candidate Count가 음수입니다."
        )

    expected_research_exists = (
        result.research_candidate_count > 0
    )

    if (
        expected_research_exists
        != result.research_candidates_exist
    ):
        raise RuntimeError(
            "Research Candidate Count와 "
            "Research Candidates Exist가 일치하지 않습니다."
        )

    if (
        result.promotion_status
        not in VALID_PROMOTION_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Promotion Status입니다: "
            f"{result.promotion_status}"
        )

    if not result.promotion_decision:
        raise RuntimeError(
            "Promotion Decision이 비어 있습니다."
        )

    if (
        result.selected_strategy_source
        not in VALID_SELECTED_STRATEGY_SOURCES
    ):
        raise RuntimeError(
            "올바르지 않은 Selected Strategy Source입니다: "
            f"{result.selected_strategy_source}"
        )

    if (
        result.selected_strategy_status
        not in VALID_SELECTED_STRATEGY_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Selected Strategy Status입니다: "
            f"{result.selected_strategy_status}"
        )

    optional_score_fields = {
        "Candidate Score": result.candidate_score,
        "Baseline Score": result.baseline_score,
        "Confidence Score": result.confidence_score,
        "Risk Score": result.risk_score,
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

    if result.risk_level not in VALID_RISK_LEVELS:
        raise RuntimeError(
            "올바르지 않은 Risk Level입니다: "
            f"{result.risk_level}"
        )

    if result.recommendation_strength is not None:
        if not 1 <= result.recommendation_strength <= 5:
            raise RuntimeError(
                "Recommendation Strength가 1~5 범위를 "
                f"벗어났습니다: "
                f"{result.recommendation_strength}"
            )

    if result.entry_score is not None:
        if result.entry_score <= 0.0:
            raise RuntimeError(
                "Entry Score가 0 이하입니다."
            )

    if result.exit_score is not None:
        if result.exit_score < 0.0:
            raise RuntimeError(
                "Exit Score가 음수입니다."
            )

    if result.stop_atr_multiple is not None:
        if result.stop_atr_multiple <= 0.0:
            raise RuntimeError(
                "Stop ATR Multiple이 0 이하입니다."
            )

    if result.target_atr_multiple is not None:
        if result.target_atr_multiple <= 0.0:
            raise RuntimeError(
                "Target ATR Multiple이 0 이하입니다."
            )

    if result.maximum_holding_days is not None:
        if result.maximum_holding_days <= 0:
            raise RuntimeError(
                "Maximum Holding Days가 0 이하입니다."
            )

    if result.position_percent is not None:
        if not 0.0 < result.position_percent <= 100.0:
            raise RuntimeError(
                "Position Percent가 올바르지 않습니다: "
                f"{result.position_percent}"
            )

    list_fields = {
        "Reasons": result.reasons,
        "Warnings": result.warnings,
        "Next Actions": result.next_actions,
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


def validate_registry_mode(
    result: ActiveStrategyRegistryResult,
) -> None:
    """
    Registry Mode 계산 결과를 검사합니다.
    """

    (
        expected_mode,
        expected_label,
    ) = calculate_expected_registry_mode(
        result
    )

    module_result = determine_registry_mode(
        active_exists=(
            result.active_strategy_exists
        ),
        paper_exists=(
            result.paper_strategy_exists
        ),
        promotion_status=(
            result.promotion_status
        ),
        research_exists=(
            result.research_candidates_exist
        ),
    )

    if module_result != (
        expected_mode,
        expected_label,
    ):
        raise RuntimeError(
            "determine_registry_mode 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.registry_mode != expected_mode:
        raise RuntimeError(
            "Registry Mode가 예상 결과와 일치하지 않습니다. "
            f"Expected={expected_mode}, "
            f"Actual={result.registry_mode}"
        )

    if result.registry_label != expected_label:
        raise RuntimeError(
            "Registry Label이 예상 결과와 일치하지 않습니다. "
            f"Expected={expected_label}, "
            f"Actual={result.registry_label}"
        )


def validate_file_flags(
    result: ActiveStrategyRegistryResult,
) -> None:
    """
    파일 존재 플래그와 실제 파일 상태를 검사합니다.
    """

    file_checks = {
        "Active Strategy": (
            result.active_strategy_exists,
            result.active_strategy_file,
        ),
        "Paper Strategy": (
            result.paper_strategy_exists,
            result.paper_strategy_file,
        ),
        "Promotion Result": (
            result.promotion_result_exists,
            result.latest_promotion_file,
        ),
        "Research Candidate": (
            result.research_candidates_exist,
            result.latest_research_file,
        ),
    }

    for field_name, (
        exists_flag,
        file_value,
    ) in file_checks.items():
        if exists_flag:
            if not file_value:
                raise RuntimeError(
                    f"{field_name} Exists가 True인데 "
                    "파일 경로가 없습니다."
                )

            file_path = Path(
                file_value
            )

            if not file_path.exists():
                raise RuntimeError(
                    f"{field_name} 파일이 실제로 "
                    f"존재하지 않습니다: {file_path}"
                )

            if file_path.stat().st_size <= 0:
                raise RuntimeError(
                    f"{field_name} 파일이 비어 있습니다."
                )

        else:
            if file_value is not None:
                raise RuntimeError(
                    f"{field_name} Exists가 False인데 "
                    "파일 경로가 기록되어 있습니다."
                )


def validate_selected_strategy(
    result: ActiveStrategyRegistryResult,
) -> None:
    """
    Registry Mode와 선택된 전략 소스가
    서로 일치하는지 검사합니다.
    """

    expected_mapping = {
        "ACTIVE": (
            "ACTIVE_STRATEGY",
            "ACTIVE",
        ),
        "PAPER_TRADING": (
            "PAPER_STRATEGY",
            "PAPER_TRADING",
        ),
        "BASELINE": (
            "PROMOTION_BASELINE",
            "BASELINE_RETAINED",
        ),
        "RESEARCH_ONLY": (
            "RESEARCH_ARCHIVE",
            "RESEARCH_ONLY",
        ),
        "UNREGISTERED": (
            "NONE",
            "UNREGISTERED",
        ),
    }

    (
        expected_source,
        expected_status,
    ) = expected_mapping[
        result.registry_mode
    ]

    if result.registry_mode == "BASELINE":
        if not result.promotion_result_exists:
            expected_source = "BASELINE_DEFAULT"
            expected_status = "BASELINE"

    if (
        result.selected_strategy_source
        != expected_source
    ):
        raise RuntimeError(
            "Selected Strategy Source가 "
            "Registry Mode와 일치하지 않습니다. "
            f"Expected={expected_source}, "
            f"Actual={result.selected_strategy_source}"
        )

    if (
        result.selected_strategy_status
        != expected_status
    ):
        raise RuntimeError(
            "Selected Strategy Status가 "
            "Registry Mode와 일치하지 않습니다. "
            f"Expected={expected_status}, "
            f"Actual={result.selected_strategy_status}"
        )

    if result.registry_mode == "UNREGISTERED":
        if result.selected_strategy_name is not None:
            raise RuntimeError(
                "UNREGISTERED 상태인데 전략 이름이 "
                "기록되어 있습니다."
            )

        if result.selected_strategy_type is not None:
            raise RuntimeError(
                "UNREGISTERED 상태인데 전략 유형이 "
                "기록되어 있습니다."
            )

    else:
        if (
            result.registry_mode != "BASELINE"
            and not result.selected_strategy_name
        ):
            raise RuntimeError(
                "등록된 전략이 있지만 "
                "Selected Strategy Name이 없습니다."
            )


def validate_current_expected_result(
    result: ActiveStrategyRegistryResult,
) -> None:
    """
    현재 AAPL V8.5 결과에 따른 예상 Registry 상태를 검사합니다.

    현재 V8.5가 BASELINE_RETAINED이므로
    Registry Mode는 BASELINE이어야 합니다.
    """

    if result.promotion_status == "BASELINE_RETAINED":
        if result.registry_mode != "BASELINE":
            raise RuntimeError(
                "최근 Promotion Status가 "
                "BASELINE_RETAINED인데 Registry Mode가 "
                "BASELINE이 아닙니다."
            )

        if (
            result.promotion_decision
            != "KEEP_BASELINE"
        ):
            raise RuntimeError(
                "BASELINE_RETAINED 상태인데 "
                "Promotion Decision이 KEEP_BASELINE이 "
                "아닙니다."
            )

        if (
            result.selected_strategy_source
            != "PROMOTION_BASELINE"
        ):
            raise RuntimeError(
                "BASELINE Registry인데 선택된 전략 소스가 "
                "PROMOTION_BASELINE이 아닙니다."
            )

        if (
            result.selected_strategy_status
            != "BASELINE_RETAINED"
        ):
            raise RuntimeError(
                "BASELINE Registry인데 선택된 전략 상태가 "
                "BASELINE_RETAINED가 아닙니다."
            )

        if not result.promotion_result_exists:
            raise RuntimeError(
                "BASELINE_RETAINED 상태인데 "
                "Promotion Result 파일이 없습니다."
            )

        if not result.research_candidates_exist:
            raise RuntimeError(
                "KEEP_BASELINE 후보가 연구 보관되었지만 "
                "Research Candidate가 없습니다."
            )

        if result.execution_enabled:
            raise RuntimeError(
                "BASELINE Registry에서 자동 실행이 "
                "활성화되어 있습니다."
            )

        if not result.manual_approval_required:
            raise RuntimeError(
                "수동 승인 요구가 비활성화되어 있습니다."
            )

        baseline_reason_exists = any(
            (
                "기준 전략"
                in str(reason)
            )
            or (
                "운영 전략을 변경하지"
                in str(reason)
            )
            for reason in result.reasons
        )

        if not baseline_reason_exists:
            raise RuntimeError(
                "기준 전략 유지 이유가 Reasons에 없습니다."
            )


def validate_evaluation_consistency(
    result: ActiveStrategyRegistryResult,
) -> None:
    """
    점수와 평가 값의 내부 일관성을 검사합니다.
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
                "Score Improvement 계산이 일치하지 않습니다. "
                f"Expected={expected_improvement:+.2f}, "
                f"Actual={result.score_improvement:+.2f}"
            )

    if result.registry_mode == "BASELINE":
        if (
            result.score_improvement is not None
            and result.score_improvement > 0.0
        ):
            raise RuntimeError(
                "BASELINE Registry인데 후보 점수가 "
                "기준 전략보다 높게 기록되었습니다."
            )


def validate_security_flags(
    result: ActiveStrategyRegistryResult,
) -> None:
    """
    자동 실행 안전 설정을 검사합니다.
    """

    if result.execution_enabled:
        raise RuntimeError(
            "V8.6 Registry에서 Execution Enabled가 "
            "True입니다. Registry 단계에서는 자동 실행이 "
            "비활성 상태여야 합니다."
        )

    if not result.manual_approval_required:
        raise RuntimeError(
            "Manual Approval Required가 False입니다."
        )

    expected_ready = (
        result.registry_mode
        in {
            "ACTIVE",
            "PAPER_TRADING",
            "BASELINE",
            "RESEARCH_ONLY",
        }
    )

    if result.registry_ready != expected_ready:
        raise RuntimeError(
            "Registry Ready 계산이 Registry Mode와 "
            "일치하지 않습니다."
        )


def validate_saved_files(
    result: ActiveStrategyRegistryResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.6 Registry 저장 파일을 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            "시간별 V8.6 Registry 보고서가 없습니다: "
            f"{report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            "V8.6 Registry Latest 파일이 없습니다: "
            f"{latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 Registry 보고서가 비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "Registry Latest 파일이 비어 있습니다."
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "시간별 Registry 보고서와 Latest 파일의 "
            "내용이 일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "registry_mode",
        "registry_label",
        "active_strategy_exists",
        "paper_strategy_exists",
        "promotion_result_exists",
        "research_candidates_exist",
        "active_strategy_file",
        "paper_strategy_file",
        "latest_promotion_file",
        "latest_research_file",
        "promotion_status",
        "promotion_decision",
        "promotion_label",
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
        "research_candidate_count",
        "registry_ready",
        "execution_enabled",
        "manual_approval_required",
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
            "저장된 V8.6 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    value_checks = {
        "version": result.version,
        "symbol": result.symbol,
        "registry_mode": result.registry_mode,
        "registry_label": result.registry_label,
        "promotion_status": result.promotion_status,
        "promotion_decision": result.promotion_decision,
        "selected_strategy_source": (
            result.selected_strategy_source
        ),
        "selected_strategy_status": (
            result.selected_strategy_status
        ),
    }

    for field_name, expected_value in (
        value_checks.items()
    ):
        if (
            str(report_payload.get(field_name))
            != str(expected_value)
        ):
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    boolean_checks = {
        "active_strategy_exists": (
            result.active_strategy_exists
        ),
        "paper_strategy_exists": (
            result.paper_strategy_exists
        ),
        "promotion_result_exists": (
            result.promotion_result_exists
        ),
        "research_candidates_exist": (
            result.research_candidates_exist
        ),
        "registry_ready": (
            result.registry_ready
        ),
        "execution_enabled": (
            result.execution_enabled
        ),
        "manual_approval_required": (
            result.manual_approval_required
        ),
    }

    for field_name, expected_value in (
        boolean_checks.items()
    ):
        if (
            bool(report_payload.get(field_name))
            != expected_value
        ):
            raise RuntimeError(
                f"저장된 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    if (
        safe_int(
            report_payload.get(
                "research_candidate_count"
            )
        )
        != result.research_candidate_count
    ):
        raise RuntimeError(
            "저장된 Research Candidate Count가 "
            "실행 결과와 일치하지 않습니다."
        )

    optional_numeric_checks = {
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
                    f"저장된 {field_name} 값은 None이어야 "
                    "하지만 값이 기록되어 있습니다."
                )

            continue

        converted_value = safe_float(
            actual_value
        )

        if converted_value is None:
            raise RuntimeError(
                f"저장된 {field_name} 값을 숫자로 "
                "변환할 수 없습니다."
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
            report_payload[
                "report_path"
            ]
        )
    )

    saved_latest_path = Path(
        str(
            report_payload[
                "latest_path"
            ]
        )
    )

    if saved_report_path != report_path:
        raise RuntimeError(
            "저장된 Report Path가 실제 경로와 "
            "일치하지 않습니다."
        )

    if saved_latest_path != latest_path:
        raise RuntimeError(
            "저장된 Latest Path가 실제 경로와 "
            "일치하지 않습니다."
        )


def print_test_result(
    result: ActiveStrategyRegistryResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.6 Registry 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V8.6 ACTIVE STRATEGY "
        "REGISTRY TEST RESULT"
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
        f"Registry label                 : "
        f"{result.registry_label}"
    )

    print(
        f"Registry ready                 : "
        f"{result.registry_ready}"
    )

    print(
        f"Execution enabled              : "
        f"{result.execution_enabled}"
    )

    print(
        f"Manual approval required       : "
        f"{result.manual_approval_required}"
    )

    print()
    print("REGISTERED FILES")
    print("-" * 140)

    print(
        f"Active strategy exists         : "
        f"{result.active_strategy_exists}"
    )

    print(
        f"Paper strategy exists          : "
        f"{result.paper_strategy_exists}"
    )

    print(
        f"Promotion result exists        : "
        f"{result.promotion_result_exists}"
    )

    print(
        f"Research candidates exist      : "
        f"{result.research_candidates_exist}"
    )

    print(
        f"Research candidate count       : "
        f"{result.research_candidate_count}"
    )

    print()
    print("LATEST PROMOTION")
    print("-" * 140)

    print(
        f"Promotion status               : "
        f"{result.promotion_status}"
    )

    print(
        f"Promotion decision             : "
        f"{result.promotion_decision}"
    )

    print(
        f"Promotion label                : "
        f"{result.promotion_label}"
    )

    print()
    print("SELECTED STRATEGY")
    print("-" * 140)

    print(
        f"Strategy source                : "
        f"{result.selected_strategy_source}"
    )

    print(
        f"Strategy status                : "
        f"{result.selected_strategy_status}"
    )

    print(
        f"Strategy name                  : "
        f"{result.selected_strategy_name}"
    )

    print(
        f"Strategy type                  : "
        f"{result.selected_strategy_type}"
    )

    print()
    print("PARAMETERS")
    print("-" * 140)

    print(
        f"Entry score                    : "
        f"{result.entry_score}"
    )

    print(
        f"Exit score                     : "
        f"{result.exit_score}"
    )

    print(
        f"Stop ATR                       : "
        f"{result.stop_atr_multiple}"
    )

    print(
        f"Target ATR                     : "
        f"{result.target_atr_multiple}"
    )

    print(
        f"Maximum holding days           : "
        f"{result.maximum_holding_days}"
    )

    print(
        f"Position percent               : "
        f"{result.position_percent}%"
    )

    print()
    print("EVALUATION")
    print("-" * 140)

    print(
        f"Candidate score                : "
        f"{result.candidate_score}/100"
    )

    print(
        f"Baseline score                 : "
        f"{result.baseline_score}/100"
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
    print("FILES")
    print("-" * 140)

    print(
        f"Active strategy file           : "
        f"{result.active_strategy_file}"
    )

    print(
        f"Paper strategy file            : "
        f"{result.paper_strategy_file}"
    )

    print(
        f"Latest promotion file          : "
        f"{result.latest_promotion_file}"
    )

    print(
        f"Latest research file           : "
        f"{result.latest_research_file}"
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
    result: ActiveStrategyRegistryResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 결과를 True/False로 출력합니다.
    """

    (
        expected_mode,
        expected_label,
    ) = calculate_expected_registry_mode(
        result
    )

    active_file_matches = (
        result.active_strategy_exists
        == (
            result.active_strategy_file is not None
            and Path(
                result.active_strategy_file
            ).exists()
        )
    )

    paper_file_matches = (
        result.paper_strategy_exists
        == (
            result.paper_strategy_file is not None
            and Path(
                result.paper_strategy_file
            ).exists()
        )
    )

    promotion_file_matches = (
        result.promotion_result_exists
        == (
            result.latest_promotion_file is not None
            and Path(
                result.latest_promotion_file
            ).exists()
        )
    )

    research_file_matches = (
        result.research_candidates_exist
        == (
            result.latest_research_file is not None
            and Path(
                result.latest_research_file
            ).exists()
        )
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

    print()
    print("=" * 140)
    print("VALIDATION CHECKS")
    print("=" * 140)

    print(
        f"Version is V8.6                   : "
        f"{result.version == 'V8.6'}"
    )

    print(
        f"Registry mode is valid            : "
        f"{result.registry_mode in VALID_REGISTRY_MODES}"
    )

    print(
        f"Registry mode matches             : "
        f"{result.registry_mode == expected_mode}"
    )

    print(
        f"Registry label matches            : "
        f"{result.registry_label == expected_label}"
    )

    print(
        f"Promotion status is valid         : "
        f"{result.promotion_status in VALID_PROMOTION_STATUSES}"
    )

    print(
        f"Active file flag matches          : "
        f"{active_file_matches}"
    )

    print(
        f"Paper file flag matches           : "
        f"{paper_file_matches}"
    )

    print(
        f"Promotion file flag matches       : "
        f"{promotion_file_matches}"
    )

    print(
        f"Research file flag matches        : "
        f"{research_file_matches}"
    )

    print(
        f"Research count matches            : "
        f"{(
            result.research_candidates_exist
            == (result.research_candidate_count > 0)
        )}"
    )

    print(
        f"Selected strategy source valid    : "
        f"{(
            result.selected_strategy_source
            in VALID_SELECTED_STRATEGY_SOURCES
        )}"
    )

    print(
        f"Selected strategy status valid    : "
        f"{(
            result.selected_strategy_status
            in VALID_SELECTED_STRATEGY_STATUSES
        )}"
    )

    print(
        f"Score improvement matches         : "
        f"{score_improvement_matches}"
    )

    print(
        f"Registry ready                    : "
        f"{result.registry_ready}"
    )

    print(
        f"Execution disabled                : "
        f"{not result.execution_enabled}"
    )

    print(
        f"Manual approval required          : "
        f"{result.manual_approval_required}"
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
    V8.6 Active Strategy Registry 통합 테스트입니다.

    다음 항목을 검사합니다.

    1. 운영 전략 파일 확인
    2. 모의투자 전략 파일 확인
    3. 최신 V8.5 승격 결과 확인
    4. 연구 후보 파일 확인
    5. 현재 Registry Mode 결정
    6. 선택 전략과 파라미터 확인
    7. 자동 실행 비활성화 확인
    8. Registry JSON 저장 및 검증
    """

    symbol = "AAPL"

    print_test_header()

    try:
        result = run_active_strategy_registry(
            symbol=symbol,
        )

        (
            report_path,
            latest_path,
        ) = save_active_strategy_registry(
            result
        )

        # 저장 경로가 결과 객체에 반영된 후
        # 최종 Registry를 다시 출력합니다.
        print_active_strategy_registry(
            result
        )

        validate_result_structure(
            result
        )

        validate_registry_mode(
            result
        )

        validate_file_flags(
            result
        )

        validate_selected_strategy(
            result
        )

        validate_current_expected_result(
            result
        )

        validate_evaluation_consistency(
            result
        )

        validate_security_flags(
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
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V8.6 active strategy registry "
            "test completed successfully."
        )

        if result.registry_mode == "BASELINE":
            print(
                "V8.5 결정에 따라 현재 기준 전략 유지 "
                "상태를 Registry에 정상 등록했습니다."
            )

        elif result.registry_mode == "ACTIVE":
            print(
                "승격된 운영 전략을 Registry에 "
                "정상 등록했습니다."
            )

        elif (
            result.registry_mode
            == "PAPER_TRADING"
        ):
            print(
                "모의투자 전략을 Registry에 "
                "정상 등록했습니다."
            )

        elif (
            result.registry_mode
            == "RESEARCH_ONLY"
        ):
            print(
                "연구 후보만 존재하는 상태를 Registry에 "
                "정상 등록했습니다."
            )

        else:
            print(
                "현재 등록 가능한 전략이 없는 상태를 "
                "정상 확인했습니다."
            )

        print(
            "주의: Registry는 전략 상태와 설정 파일만 "
            "관리하며 실제 증권 주문이나 자동 매매를 "
            "실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V8.6 Active Strategy Registry "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V8.6 ACTIVE STRATEGY "
            "REGISTRY ERROR"
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