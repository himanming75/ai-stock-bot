import json
from pathlib import Path
from typing import Any

from backtest.strategy_promotion_manager import (
    StrategyPromotionResult,
    VALID_PROMOTION_STATUSES,
    VALID_SOURCE_DECISIONS,
    determine_promotion_status,
    print_strategy_promotion_result,
    run_strategy_promotion,
    save_strategy_promotion_result,
)


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
    V8.5 Strategy Promotion Manager
    테스트 제목을 출력합니다.
    """

    print()
    print("=" * 135)
    print(
        "AI STOCK BOT V8.5 "
        "STRATEGY PROMOTION MANAGER TEST"
    )
    print("=" * 135)


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


def load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽고 Dictionary인지 확인합니다.
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


def calculate_expected_promotion_status(
    source_decision: str,
) -> tuple[str, str]:
    """
    V8.4 Decision에 해당하는 V8.5 상태를
    독립적으로 다시 계산합니다.
    """

    decision_mapping = {
        "APPLY_CANDIDATE": (
            "PROMOTED",
            "후보 전략 승격",
        ),
        "PAPER_TRADE_CANDIDATE": (
            "PAPER_TRADING",
            "모의투자 전략 등록",
        ),
        "KEEP_BASELINE": (
            "BASELINE_RETAINED",
            "기존 전략 유지",
        ),
        "RESEARCH_ONLY": (
            "RESEARCH_ARCHIVED",
            "연구 후보 보관",
        ),
        "NO_DECISION": (
            "NO_ACTION",
            "변경 없음",
        ),
    }

    return decision_mapping.get(
        source_decision.strip().upper(),
        (
            "NO_ACTION",
            "변경 없음",
        ),
    )


def validate_result_structure(
    result: StrategyPromotionResult,
) -> None:
    """
    V8.5 결과의 필수 필드, 자료형,
    값의 범위를 검사합니다.
    """

    if result.version != "V8.5":
        raise RuntimeError(
            f"보고서 버전이 V8.5가 아닙니다: "
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
            "Created At 값이 비어 있습니다."
        )

    if not result.source_file:
        raise RuntimeError(
            "Source File이 비어 있습니다."
        )

    source_path = Path(
        result.source_file
    )

    if not source_path.exists():
        raise RuntimeError(
            "V8.4 Source File이 존재하지 않습니다: "
            f"{source_path}"
        )

    if (
        result.source_decision
        not in VALID_SOURCE_DECISIONS
    ):
        raise RuntimeError(
            "올바르지 않은 Source Decision입니다: "
            f"{result.source_decision}"
        )

    if (
        result.promotion_status
        not in VALID_PROMOTION_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Promotion Status입니다: "
            f"{result.promotion_status}"
        )

    if not result.source_decision_label:
        raise RuntimeError(
            "Source Decision Label이 비어 있습니다."
        )

    if not result.promotion_label:
        raise RuntimeError(
            "Promotion Label이 비어 있습니다."
        )

    boolean_fields = {
        "Action Performed": result.action_performed,
        "Baseline Retained": result.baseline_retained,
        "Candidate Promoted": result.candidate_promoted,
        "Candidate Paper Trading": (
            result.candidate_paper_trading
        ),
        "Candidate Archived": result.candidate_archived,
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(
            value,
            bool,
        ):
            raise RuntimeError(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if result.selected_candidate_number is None:
        raise RuntimeError(
            "Selected Candidate Number가 없습니다."
        )

    if result.selected_candidate_number < 0:
        raise RuntimeError(
            "Selected Candidate Number가 음수입니다."
        )

    if not result.selected_candidate_name:
        raise RuntimeError(
            "Selected Candidate Name이 비어 있습니다."
        )

    if not result.selected_candidate_type:
        raise RuntimeError(
            "Selected Candidate Type이 비어 있습니다."
        )

    score_fields = {
        "Candidate Score": result.candidate_score,
        "Baseline Score": result.baseline_score,
        "Confidence Score": result.confidence_score,
        "Risk Score": result.risk_score,
    }

    for field_name, value in score_fields.items():
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

    if not 1 <= result.recommendation_strength <= 5:
        raise RuntimeError(
            "Recommendation Strength가 1~5 범위를 "
            f"벗어났습니다: "
            f"{result.recommendation_strength}"
        )

    if result.entry_score is None:
        raise RuntimeError(
            "Entry Score가 없습니다."
        )

    if result.exit_score is None:
        raise RuntimeError(
            "Exit Score가 없습니다."
        )

    if result.stop_atr_multiple is None:
        raise RuntimeError(
            "Stop ATR Multiple이 없습니다."
        )

    if result.target_atr_multiple is None:
        raise RuntimeError(
            "Target ATR Multiple이 없습니다."
        )

    if result.maximum_holding_days is None:
        raise RuntimeError(
            "Maximum Holding Days가 없습니다."
        )

    if result.position_percent is None:
        raise RuntimeError(
            "Position Percent가 없습니다."
        )

    if result.entry_score <= 0.0:
        raise RuntimeError(
            "Entry Score가 0 이하입니다."
        )

    if result.exit_score < 0.0:
        raise RuntimeError(
            "Exit Score가 음수입니다."
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


def validate_score_calculation(
    result: StrategyPromotionResult,
) -> None:
    """
    기준 전략과 후보 전략의 점수 차이를 검사합니다.
    """

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


def validate_status_mapping(
    result: StrategyPromotionResult,
) -> None:
    """
    Source Decision과 Promotion Status의
    매핑이 올바른지 검사합니다.
    """

    (
        expected_status,
        expected_label,
    ) = calculate_expected_promotion_status(
        result.source_decision
    )

    module_status = determine_promotion_status(
        result.source_decision
    )

    if module_status != (
        expected_status,
        expected_label,
    ):
        raise RuntimeError(
            "determine_promotion_status 함수 결과가 "
            "독립 계산 결과와 일치하지 않습니다."
        )

    if result.promotion_status != expected_status:
        raise RuntimeError(
            "Promotion Status가 Source Decision 규칙과 "
            "일치하지 않습니다. "
            f"Expected={expected_status}, "
            f"Actual={result.promotion_status}"
        )

    if result.promotion_label != expected_label:
        raise RuntimeError(
            "Promotion Label이 Source Decision 규칙과 "
            "일치하지 않습니다. "
            f"Expected={expected_label}, "
            f"Actual={result.promotion_label}"
        )


def validate_action_flags(
    result: StrategyPromotionResult,
) -> None:
    """
    Promotion Status별 행동 플래그를 검사합니다.
    """

    flag_count = sum(
        [
            int(result.baseline_retained),
            int(result.candidate_promoted),
            int(result.candidate_paper_trading),
            int(result.candidate_archived),
        ]
    )

    if result.promotion_status == "PROMOTED":
        if not result.action_performed:
            raise RuntimeError(
                "PROMOTED 상태인데 Action Performed가 "
                "False입니다."
            )

        if not result.candidate_promoted:
            raise RuntimeError(
                "PROMOTED 상태인데 Candidate Promoted가 "
                "False입니다."
            )

        if result.baseline_retained:
            raise RuntimeError(
                "PROMOTED 상태인데 Baseline Retained가 "
                "True입니다."
            )

        if result.candidate_paper_trading:
            raise RuntimeError(
                "PROMOTED 상태인데 Paper Trading도 "
                "True입니다."
            )

        if result.candidate_archived:
            raise RuntimeError(
                "PROMOTED 상태인데 Candidate Archived도 "
                "True입니다."
            )

        if flag_count != 1:
            raise RuntimeError(
                "PROMOTED 상태의 행동 플래그 개수가 "
                "올바르지 않습니다."
            )

    elif result.promotion_status == "PAPER_TRADING":
        if not result.action_performed:
            raise RuntimeError(
                "PAPER_TRADING 상태인데 "
                "Action Performed가 False입니다."
            )

        if not result.candidate_paper_trading:
            raise RuntimeError(
                "PAPER_TRADING 상태인데 "
                "Candidate Paper Trading이 False입니다."
            )

        if flag_count != 1:
            raise RuntimeError(
                "PAPER_TRADING 상태의 행동 플래그 개수가 "
                "올바르지 않습니다."
            )

    elif result.promotion_status == "BASELINE_RETAINED":
        if not result.action_performed:
            raise RuntimeError(
                "BASELINE_RETAINED 상태인데 "
                "Action Performed가 False입니다."
            )

        if not result.baseline_retained:
            raise RuntimeError(
                "BASELINE_RETAINED 상태인데 "
                "Baseline Retained가 False입니다."
            )

        if not result.candidate_archived:
            raise RuntimeError(
                "BASELINE_RETAINED 상태인데 후보가 "
                "연구 기록으로 보관되지 않았습니다."
            )

        if result.candidate_promoted:
            raise RuntimeError(
                "BASELINE_RETAINED 상태인데 Candidate가 "
                "승격되었습니다."
            )

        if result.candidate_paper_trading:
            raise RuntimeError(
                "BASELINE_RETAINED 상태인데 Candidate가 "
                "모의투자로 등록되었습니다."
            )

        # 기존 전략 유지와 후보 보관 두 가지가
        # 동시에 True인 것이 정상입니다.
        if flag_count != 2:
            raise RuntimeError(
                "BASELINE_RETAINED 상태의 행동 플래그 "
                "개수가 올바르지 않습니다."
            )

    elif result.promotion_status == "RESEARCH_ARCHIVED":
        if not result.action_performed:
            raise RuntimeError(
                "RESEARCH_ARCHIVED 상태인데 "
                "Action Performed가 False입니다."
            )

        if not result.candidate_archived:
            raise RuntimeError(
                "RESEARCH_ARCHIVED 상태인데 "
                "Candidate Archived가 False입니다."
            )

        if flag_count != 1:
            raise RuntimeError(
                "RESEARCH_ARCHIVED 상태의 행동 플래그 "
                "개수가 올바르지 않습니다."
            )

    elif result.promotion_status == "NO_ACTION":
        if result.action_performed:
            raise RuntimeError(
                "NO_ACTION 상태인데 Action Performed가 "
                "True입니다."
            )

        if flag_count != 0:
            raise RuntimeError(
                "NO_ACTION 상태인데 행동 플래그가 "
                "활성화되어 있습니다."
            )


def validate_strategy_output_file(
    result: StrategyPromotionResult,
) -> None:
    """
    Promotion Status에 따라 생성된 전략 파일을 검사합니다.
    """

    if result.promotion_status == "NO_ACTION":
        if result.strategy_output_file is not None:
            raise RuntimeError(
                "NO_ACTION 상태인데 Strategy Output File이 "
                "생성되었습니다."
            )

        return

    if not result.strategy_output_file:
        raise RuntimeError(
            "Action이 수행됐지만 Strategy Output File이 "
            "없습니다."
        )

    strategy_path = Path(
        result.strategy_output_file
    )

    if not strategy_path.exists():
        raise RuntimeError(
            "Strategy Output File이 실제로 존재하지 "
            f"않습니다: {strategy_path}"
        )

    if strategy_path.stat().st_size <= 0:
        raise RuntimeError(
            "Strategy Output File이 비어 있습니다."
        )

    payload = load_json_file(
        strategy_path
    )

    required_keys = {
        "version",
        "symbol",
        "strategy_status",
        "created_at",
        "source_version",
        "source_decision",
        "candidate",
        "parameters",
        "evaluation",
        "source_file",
    }

    missing_keys = (
        required_keys
        - set(payload.keys())
    )

    if missing_keys:
        raise RuntimeError(
            "Strategy Output JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    if str(payload["version"]) != "V8.5":
        raise RuntimeError(
            "Strategy Output JSON의 Version이 "
            "V8.5가 아닙니다."
        )

    if str(payload["symbol"]) != result.symbol:
        raise RuntimeError(
            "Strategy Output JSON의 Symbol이 "
            "실행 결과와 일치하지 않습니다."
        )

    if (
        str(payload["source_decision"])
        != result.source_decision
    ):
        raise RuntimeError(
            "Strategy Output JSON의 Source Decision이 "
            "실행 결과와 일치하지 않습니다."
        )

    candidate = payload.get(
        "candidate"
    )

    parameters = payload.get(
        "parameters"
    )

    evaluation = payload.get(
        "evaluation"
    )

    if not isinstance(
        candidate,
        dict,
    ):
        raise RuntimeError(
            "Strategy Output의 Candidate가 "
            "Dictionary가 아닙니다."
        )

    if not isinstance(
        parameters,
        dict,
    ):
        raise RuntimeError(
            "Strategy Output의 Parameters가 "
            "Dictionary가 아닙니다."
        )

    if not isinstance(
        evaluation,
        dict,
    ):
        raise RuntimeError(
            "Strategy Output의 Evaluation이 "
            "Dictionary가 아닙니다."
        )

    if (
        str(candidate.get("name"))
        != result.selected_candidate_name
    ):
        raise RuntimeError(
            "Strategy Output의 Candidate Name이 "
            "실행 결과와 일치하지 않습니다."
        )

    if (
        safe_int(candidate.get("number"))
        != result.selected_candidate_number
    ):
        raise RuntimeError(
            "Strategy Output의 Candidate Number가 "
            "실행 결과와 일치하지 않습니다."
        )

    parameter_checks = {
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
        parameter_checks.items()
    ):
        actual_value = parameters.get(
            field_name
        )

        if abs(
            safe_float(actual_value)
            - safe_float(expected_value)
        ) > 0.01:
            raise RuntimeError(
                f"Strategy Output의 {field_name} 값이 "
                "실행 결과와 일치하지 않습니다."
            )

    if abs(
        safe_float(
            evaluation.get(
                "candidate_score"
            )
        )
        - result.candidate_score
    ) > 0.01:
        raise RuntimeError(
            "Strategy Output의 Candidate Score가 "
            "실행 결과와 일치하지 않습니다."
        )

    if abs(
        safe_float(
            evaluation.get(
                "baseline_score"
            )
        )
        - result.baseline_score
    ) > 0.01:
        raise RuntimeError(
            "Strategy Output의 Baseline Score가 "
            "실행 결과와 일치하지 않습니다."
        )

    expected_strategy_status = {
        "PROMOTED": "ACTIVE",
        "PAPER_TRADING": "PAPER_TRADING",
        "BASELINE_RETAINED": "RESEARCH_ONLY",
        "RESEARCH_ARCHIVED": "RESEARCH_ONLY",
    }.get(
        result.promotion_status
    )

    if (
        expected_strategy_status is not None
        and str(
            payload.get(
                "strategy_status"
            )
        )
        != expected_strategy_status
    ):
        raise RuntimeError(
            "Strategy Output의 Strategy Status가 "
            "Promotion Status와 일치하지 않습니다. "
            f"Expected={expected_strategy_status}, "
            f"Actual={payload.get('strategy_status')}"
        )


def validate_current_expected_result(
    result: StrategyPromotionResult,
) -> None:
    """
    현재 AAPL V8.4 결과에 따른 예상 상태를 검사합니다.

    현재 V8.4 Decision은 KEEP_BASELINE이므로
    BASELINE_RETAINED가 정상입니다.
    """

    if result.source_decision == "KEEP_BASELINE":
        if (
            result.promotion_status
            != "BASELINE_RETAINED"
        ):
            raise RuntimeError(
                "KEEP_BASELINE Decision인데 "
                "Promotion Status가 BASELINE_RETAINED가 "
                "아닙니다."
            )

        if not result.baseline_retained:
            raise RuntimeError(
                "KEEP_BASELINE인데 기존 전략 유지 "
                "플래그가 False입니다."
            )

        if result.candidate_promoted:
            raise RuntimeError(
                "KEEP_BASELINE인데 후보 전략이 "
                "승격되었습니다."
            )

        if result.candidate_paper_trading:
            raise RuntimeError(
                "KEEP_BASELINE인데 후보 전략이 "
                "모의투자로 등록되었습니다."
            )

        if not result.candidate_archived:
            raise RuntimeError(
                "KEEP_BASELINE인데 후보 전략이 "
                "연구 기록으로 보관되지 않았습니다."
            )

        if result.score_improvement > 0.0:
            raise RuntimeError(
                "현재 KEEP_BASELINE 결과인데 후보 점수가 "
                "기준 전략보다 높게 기록되었습니다."
            )

        baseline_reason_exists = any(
            (
                "기준 전략"
                in str(reason)
            )
            or (
                "기존 운영 전략"
                in str(reason)
            )
            for reason in result.reasons
        )

        if not baseline_reason_exists:
            raise RuntimeError(
                "기존 전략 유지 이유가 Reasons에 "
                "포함되지 않았습니다."
            )

        retain_action_exists = any(
            (
                "기준 전략"
                in str(action)
            )
            or (
                "현재"
                in str(action)
                and "유지"
                in str(action)
            )
            for action in result.next_actions
        )

        if not retain_action_exists:
            raise RuntimeError(
                "기준 전략 유지 작업이 Next Actions에 "
                "포함되지 않았습니다."
            )


def validate_saved_files(
    result: StrategyPromotionResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.5 보고서 파일과 Latest 파일을 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            "시간별 V8.5 Promotion 보고서가 없습니다: "
            f"{report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            "V8.5 Promotion Latest 파일이 없습니다: "
            f"{latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 V8.5 Promotion 보고서가 "
            "비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "V8.5 Promotion Latest 파일이 "
            "비어 있습니다."
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "시간별 V8.5 보고서와 Latest 보고서의 "
            "내용이 일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_file",
        "source_decision",
        "source_decision_label",
        "promotion_status",
        "promotion_label",
        "action_performed",
        "baseline_retained",
        "candidate_promoted",
        "candidate_paper_trading",
        "candidate_archived",
        "selected_candidate_number",
        "selected_candidate_name",
        "selected_candidate_type",
        "candidate_score",
        "baseline_score",
        "score_improvement",
        "confidence_score",
        "confidence_level",
        "risk_score",
        "risk_level",
        "recommendation_strength",
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
        "previous_active_strategy_file",
        "strategy_output_file",
        "history_file",
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
            "저장된 V8.5 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    if (
        str(report_payload["version"])
        != result.version
    ):
        raise RuntimeError(
            "저장된 Version이 실행 결과와 "
            "일치하지 않습니다."
        )

    if (
        str(report_payload["symbol"])
        != result.symbol
    ):
        raise RuntimeError(
            "저장된 Symbol이 실행 결과와 "
            "일치하지 않습니다."
        )

    if (
        str(
            report_payload[
                "source_decision"
            ]
        )
        != result.source_decision
    ):
        raise RuntimeError(
            "저장된 Source Decision이 실행 결과와 "
            "일치하지 않습니다."
        )

    if (
        str(
            report_payload[
                "promotion_status"
            ]
        )
        != result.promotion_status
    ):
        raise RuntimeError(
            "저장된 Promotion Status가 실행 결과와 "
            "일치하지 않습니다."
        )

    if abs(
        safe_float(
            report_payload[
                "score_improvement"
            ]
        )
        - result.score_improvement
    ) > 0.01:
        raise RuntimeError(
            "저장된 Score Improvement가 실행 결과와 "
            "일치하지 않습니다."
        )

    if (
        bool(
            report_payload[
                "baseline_retained"
            ]
        )
        != result.baseline_retained
    ):
        raise RuntimeError(
            "저장된 Baseline Retained가 실행 결과와 "
            "일치하지 않습니다."
        )

    if (
        str(
            report_payload.get(
                "strategy_output_file"
            )
        )
        != str(result.strategy_output_file)
    ):
        raise RuntimeError(
            "저장된 Strategy Output File이 실행 결과와 "
            "일치하지 않습니다."
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
            "저장된 Report Path가 실제 보고서 경로와 "
            "일치하지 않습니다."
        )

    if saved_latest_path != latest_path:
        raise RuntimeError(
            "저장된 Latest Path가 실제 Latest 경로와 "
            "일치하지 않습니다."
        )


def print_validation_checks(
    result: StrategyPromotionResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 테스트 결과를 True/False로 출력합니다.
    """

    (
        expected_status,
        expected_label,
    ) = calculate_expected_promotion_status(
        result.source_decision
    )

    expected_improvement = round(
        result.candidate_score
        - result.baseline_score,
        2,
    )

    source_exists = Path(
        result.source_file
    ).exists()

    strategy_output_exists = (
        result.strategy_output_file is not None
        and Path(
            result.strategy_output_file
        ).exists()
    )

    score_improvement_matches = (
        abs(
            expected_improvement
            - result.score_improvement
        )
        <= 0.01
    )

    status_matches = (
        result.promotion_status
        == expected_status
    )

    label_matches = (
        result.promotion_label
        == expected_label
    )

    print()
    print("=" * 135)
    print("VALIDATION CHECKS")
    print("=" * 135)

    print(
        f"Version is V8.5                 : "
        f"{result.version == 'V8.5'}"
    )

    print(
        f"Source file exists              : "
        f"{source_exists}"
    )

    print(
        f"Source decision is valid        : "
        f"{result.source_decision in VALID_SOURCE_DECISIONS}"
    )

    print(
        f"Promotion status is valid       : "
        f"{result.promotion_status in VALID_PROMOTION_STATUSES}"
    )

    print(
        f"Promotion status matches        : "
        f"{status_matches}"
    )

    print(
        f"Promotion label matches         : "
        f"{label_matches}"
    )

    print(
        f"Score improvement matches       : "
        f"{score_improvement_matches}"
    )

    print(
        f"Action performed                : "
        f"{result.action_performed}"
    )

    print(
        f"Baseline retained               : "
        f"{result.baseline_retained}"
    )

    print(
        f"Candidate promoted              : "
        f"{result.candidate_promoted}"
    )

    print(
        f"Paper trading registered        : "
        f"{result.candidate_paper_trading}"
    )

    print(
        f"Research candidate archived     : "
        f"{result.candidate_archived}"
    )

    print(
        f"Strategy output file exists     : "
        f"{strategy_output_exists}"
    )

    print(
        f"Reasons exist                   : "
        f"{bool(result.reasons)}"
    )

    print(
        f"Warnings exist                  : "
        f"{bool(result.warnings)}"
    )

    print(
        f"Next actions exist              : "
        f"{bool(result.next_actions)}"
    )

    print(
        f"Report file exists              : "
        f"{report_path.exists()}"
    )

    print(
        f"Latest file exists              : "
        f"{latest_path.exists()}"
    )

    print("=" * 135)


def print_test_result(
    result: StrategyPromotionResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.5 테스트 결과를 요약 출력합니다.
    """

    print()
    print("=" * 135)
    print(
        "V8.5 STRATEGY PROMOTION "
        "MANAGER TEST RESULT"
    )
    print("=" * 135)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

    print(
        f"Source decision                : "
        f"{result.source_decision}"
    )

    print(
        f"Source decision label          : "
        f"{result.source_decision_label}"
    )

    print(
        f"Promotion status               : "
        f"{result.promotion_status}"
    )

    print(
        f"Promotion label                : "
        f"{result.promotion_label}"
    )

    print(
        f"Action performed               : "
        f"{result.action_performed}"
    )

    print()
    print("STRATEGY ACTION")
    print("-" * 135)

    print(
        f"Baseline retained              : "
        f"{result.baseline_retained}"
    )

    print(
        f"Candidate promoted             : "
        f"{result.candidate_promoted}"
    )

    print(
        f"Paper trading registered       : "
        f"{result.candidate_paper_trading}"
    )

    print(
        f"Research candidate archived    : "
        f"{result.candidate_archived}"
    )

    print()
    print("SELECTED CANDIDATE")
    print("-" * 135)

    print(
        f"Candidate number               : "
        f"{result.selected_candidate_number}"
    )

    print(
        f"Candidate name                 : "
        f"{result.selected_candidate_name}"
    )

    print(
        f"Candidate type                 : "
        f"{result.selected_candidate_type}"
    )

    print()
    print("SCORE COMPARISON")
    print("-" * 135)

    print(
        f"Baseline score                 : "
        f"{result.baseline_score:.2f}/100"
    )

    print(
        f"Candidate score                : "
        f"{result.candidate_score:.2f}/100"
    )

    print(
        f"Score improvement              : "
        f"{result.score_improvement:+.2f} points"
    )

    print(
        f"Confidence                     : "
        f"{result.confidence_score:.2f}/100 "
        f"({result.confidence_level})"
    )

    print(
        f"Risk                           : "
        f"{result.risk_score:.2f}/100 "
        f"({result.risk_level})"
    )

    print(
        f"Recommendation strength        : "
        f"{result.recommendation_strength}/5"
    )

    print()
    print("PARAMETERS")
    print("-" * 135)

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
    print("FILES")
    print("-" * 135)

    print(
        f"Source file                    : "
        f"{result.source_file}"
    )

    print(
        f"Strategy output file           : "
        f"{result.strategy_output_file}"
    )

    print(
        f"Previous active backup         : "
        f"{result.previous_active_strategy_file}"
    )

    print(
        f"History file                   : "
        f"{result.history_file}"
    )

    print(
        f"Report file                    : "
        f"{report_path}"
    )

    print(
        f"Latest file                    : "
        f"{latest_path}"
    )

    print("=" * 135)


def main() -> None:
    """
    V8.5 Strategy Promotion Manager 통합 테스트입니다.

    현재 V8.4 Recommendation 결과를 읽어서:

    1. Decision을 Promotion Status로 변환
    2. 기존 전략 유지 또는 후보 전략 분류
    3. 전략 설정 JSON 파일 생성
    4. 처리 결과 보고서 저장
    5. 행동 플래그와 저장된 JSON 내용 검증

    을 수행합니다.
    """

    symbol = "AAPL"

    print_test_header()

    try:
        result = run_strategy_promotion(
            symbol=symbol,
        )

        (
            report_path,
            latest_path,
        ) = save_strategy_promotion_result(
            result
        )

        # 저장 경로가 결과 객체에 반영된 후
        # 최종 결과를 다시 출력합니다.
        print_strategy_promotion_result(
            result
        )

        validate_result_structure(
            result
        )

        validate_score_calculation(
            result
        )

        validate_status_mapping(
            result
        )

        validate_action_flags(
            result
        )

        validate_strategy_output_file(
            result
        )

        validate_current_expected_result(
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
            "V8.5 strategy promotion manager "
            "test completed successfully."
        )

        if (
            result.promotion_status
            == "BASELINE_RETAINED"
        ):
            print(
                "V8.4 결정에 따라 기존 전략을 유지하고 "
                "후보 전략을 연구 기록으로 정상 "
                "보관했습니다."
            )

        elif (
            result.promotion_status
            == "PROMOTED"
        ):
            print(
                "V8.4 결정에 따라 후보 전략을 운영 "
                "전략으로 정상 승격했습니다."
            )

        elif (
            result.promotion_status
            == "PAPER_TRADING"
        ):
            print(
                "V8.4 결정에 따라 후보 전략을 "
                "모의투자 전략으로 정상 등록했습니다."
            )

        elif (
            result.promotion_status
            == "RESEARCH_ARCHIVED"
        ):
            print(
                "V8.4 결정에 따라 후보 전략을 "
                "연구용 전략으로 정상 보관했습니다."
            )

        else:
            print(
                "V8.4 Decision에 따라 전략 변경 없이 "
                "정상 종료했습니다."
            )

        print(
            "주의: 이 모듈은 전략 설정과 연구 파일만 "
            "관리하며 실제 증권 주문을 실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 135)
        print("TEST CANCELLED")
        print("=" * 135)

        print(
            "사용자가 V8.5 Strategy Promotion Manager "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 135)
        print(
            "V8.5 STRATEGY PROMOTION "
            "MANAGER ERROR"
        )
        print("=" * 135)

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