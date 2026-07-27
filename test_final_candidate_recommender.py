import json
from pathlib import Path
from typing import Any

from backtest.final_candidate_recommender import (
    FinalCandidateRecommendation,
    VALID_CONFIDENCE_LEVELS,
    VALID_DECISIONS,
    VALID_RISK_LEVELS,
    build_star_rating,
    print_final_candidate_recommendation,
    run_final_candidate_recommendation,
    save_final_candidate_recommendation,
)


VALID_CANDIDATE_STATUSES = {
    "ROBUST",
    "ACCEPTABLE",
    "WEAK",
    "REJECTED",
}

VALID_WALK_FORWARD_STATUSES = {
    "ROBUST",
    "ACCEPTABLE",
    "WEAK",
    "FAILED",
    "UNKNOWN",
}


def print_test_header() -> None:
    """
    V8.4 Final Candidate Recommender
    테스트 제목을 출력합니다.
    """

    print()
    print("=" * 130)
    print(
        "AI STOCK BOT V8.4 "
        "FINAL CANDIDATE RECOMMENDER TEST"
    )
    print("=" * 130)


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
    저장된 JSON 파일을 읽습니다.
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
            "저장된 JSON의 최상위 값이 "
            "Dictionary 형식이 아닙니다."
        )

    return payload


def calculate_expected_decision(
    result: FinalCandidateRecommendation,
) -> str:
    """
    V8.4 결정 규칙을 독립적으로 다시 계산합니다.
    """

    if not result.passed_all_checks:
        return "RESEARCH_ONLY"

    if (
        result.score_improvement >= 3.0
        and result.confidence_score >= 75.0
        and result.risk_score <= 50.0
        and result.walk_forward_status
        in {
            "ROBUST",
            "ACCEPTABLE",
        }
    ):
        return "APPLY_CANDIDATE"

    if (
        result.score_improvement > 0.0
        and result.confidence_score >= 65.0
        and result.risk_score <= 60.0
    ):
        return "PAPER_TRADE_CANDIDATE"

    if (
        result.score_improvement <= 0.0
        and result.baseline_score
        >= result.selected_candidate_score
    ):
        return "KEEP_BASELINE"

    return "RESEARCH_ONLY"


def calculate_expected_confidence_level(
    confidence_score: float,
) -> str:
    """
    신뢰도 점수에 맞는 등급을 다시 계산합니다.
    """

    if confidence_score >= 80.0:
        return "HIGH"

    if confidence_score >= 60.0:
        return "MEDIUM"

    return "LOW"


def calculate_expected_risk_level(
    risk_score: float,
) -> str:
    """
    위험 점수에 맞는 등급을 다시 계산합니다.
    """

    if risk_score <= 35.0:
        return "LOW"

    if risk_score <= 60.0:
        return "MEDIUM"

    return "HIGH"


def validate_result_structure(
    result: FinalCandidateRecommendation,
) -> None:
    """
    V8.4 추천 결과의 필수 필드와 값 범위를 검사합니다.
    """

    if result.version != "V8.4":
        raise RuntimeError(
            f"보고서 버전이 V8.4가 아닙니다: "
            f"{result.version}"
        )

    if not result.symbol:
        raise RuntimeError(
            "Symbol 값이 비어 있습니다."
        )

    if result.symbol != result.symbol.upper():
        raise RuntimeError(
            "Symbol이 대문자로 정규화되지 않았습니다."
        )

    if not result.source_file:
        raise RuntimeError(
            "Source File 값이 비어 있습니다."
        )

    source_path = Path(
        result.source_file
    )

    if not source_path.exists():
        raise RuntimeError(
            f"Source File이 실제로 존재하지 않습니다: "
            f"{source_path}"
        )

    if result.decision not in VALID_DECISIONS:
        raise RuntimeError(
            f"올바르지 않은 Decision입니다: "
            f"{result.decision}"
        )

    if not result.decision_label:
        raise RuntimeError(
            "Decision Label이 비어 있습니다."
        )

    if (
        result.confidence_level
        not in VALID_CONFIDENCE_LEVELS
    ):
        raise RuntimeError(
            f"올바르지 않은 Confidence Level입니다: "
            f"{result.confidence_level}"
        )

    if result.risk_level not in VALID_RISK_LEVELS:
        raise RuntimeError(
            f"올바르지 않은 Risk Level입니다: "
            f"{result.risk_level}"
        )

    if not 0.0 <= result.confidence_score <= 100.0:
        raise RuntimeError(
            "Confidence Score가 0~100 범위를 "
            f"벗어났습니다: {result.confidence_score}"
        )

    if not 0.0 <= result.risk_score <= 100.0:
        raise RuntimeError(
            "Risk Score가 0~100 범위를 "
            f"벗어났습니다: {result.risk_score}"
        )

    if not 0.0 <= result.baseline_score <= 100.0:
        raise RuntimeError(
            "Baseline Score가 0~100 범위를 "
            f"벗어났습니다: {result.baseline_score}"
        )

    if not (
        0.0
        <= result.selected_candidate_score
        <= 100.0
    ):
        raise RuntimeError(
            "Selected Candidate Score가 0~100 범위를 "
            f"벗어났습니다: "
            f"{result.selected_candidate_score}"
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

    if (
        result.selected_candidate_status
        not in VALID_CANDIDATE_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Selected Candidate "
            f"Status입니다: "
            f"{result.selected_candidate_status}"
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

    if not 0.0 <= result.win_rate_percent <= 100.0:
        raise RuntimeError(
            "Win Rate가 0~100 범위를 벗어났습니다: "
            f"{result.win_rate_percent}"
        )

    if result.total_trades < 0:
        raise RuntimeError(
            "Total Trades가 음수입니다."
        )

    if (
        result.walk_forward_status
        not in VALID_WALK_FORWARD_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Walk-Forward Status입니다: "
            f"{result.walk_forward_status}"
        )

    percentage_fields = {
        "Walk-Forward Score": (
            result.walk_forward_score
        ),
        "Profitable Windows": (
            result.profitable_windows_percent
        ),
        "Acceptable Windows": (
            result.acceptable_windows_percent
        ),
        "Beat Default Return": (
            result.beat_default_return_percent
        ),
        "Parameter Stability": (
            result.parameter_stability_score
        ),
    }

    for field_name, value in percentage_fields.items():
        if not 0.0 <= value <= 100.0:
            raise RuntimeError(
                f"{field_name}가 0~100 범위를 "
                f"벗어났습니다: {value}"
            )

    if not isinstance(
        result.backtest_success,
        bool,
    ):
        raise RuntimeError(
            "Backtest Success가 bool이 아닙니다."
        )

    if not isinstance(
        result.walk_forward_success,
        bool,
    ):
        raise RuntimeError(
            "Walk-Forward Success가 bool이 아닙니다."
        )

    if not isinstance(
        result.passed_all_checks,
        bool,
    ):
        raise RuntimeError(
            "Passed All Checks가 bool이 아닙니다."
        )

    if not 1 <= result.recommendation_strength <= 5:
        raise RuntimeError(
            "Recommendation Strength가 1~5 범위를 "
            f"벗어났습니다: "
            f"{result.recommendation_strength}"
        )

    if not isinstance(
        result.reasons,
        list,
    ):
        raise RuntimeError(
            "Reasons가 List가 아닙니다."
        )

    if not isinstance(
        result.concerns,
        list,
    ):
        raise RuntimeError(
            "Concerns가 List가 아닙니다."
        )

    if not isinstance(
        result.required_actions,
        list,
    ):
        raise RuntimeError(
            "Required Actions가 List가 아닙니다."
        )

    if not result.required_actions:
        raise RuntimeError(
            "Required Actions가 비어 있습니다."
        )


def validate_calculations(
    result: FinalCandidateRecommendation,
) -> None:
    """
    V8.4 핵심 계산과 최종 결정을 검사합니다.
    """

    expected_improvement = round(
        result.selected_candidate_score
        - result.baseline_score,
        2,
    )

    if abs(
        expected_improvement
        - result.score_improvement
    ) > 0.01:
        raise RuntimeError(
            "Score Improvement 계산이 일치하지 않습니다. "
            f"Expected={expected_improvement:.2f}, "
            f"Actual={result.score_improvement:.2f}"
        )

    expected_confidence_level = (
        calculate_expected_confidence_level(
            result.confidence_score
        )
    )

    if (
        expected_confidence_level
        != result.confidence_level
    ):
        raise RuntimeError(
            "Confidence Level 계산이 일치하지 않습니다. "
            f"Expected={expected_confidence_level}, "
            f"Actual={result.confidence_level}"
        )

    expected_risk_level = (
        calculate_expected_risk_level(
            result.risk_score
        )
    )

    if expected_risk_level != result.risk_level:
        raise RuntimeError(
            "Risk Level 계산이 일치하지 않습니다. "
            f"Expected={expected_risk_level}, "
            f"Actual={result.risk_level}"
        )

    expected_decision = calculate_expected_decision(
        result
    )

    if expected_decision != result.decision:
        raise RuntimeError(
            "Final Decision 계산이 일치하지 않습니다. "
            f"Expected={expected_decision}, "
            f"Actual={result.decision}"
        )

    star_rating = build_star_rating(
        result.recommendation_strength
    )

    if len(star_rating) != 5:
        raise RuntimeError(
            "Star Rating의 길이가 5가 아닙니다."
        )

    filled_stars = star_rating.count(
        "★"
    )

    empty_stars = star_rating.count(
        "☆"
    )

    if (
        filled_stars
        != result.recommendation_strength
    ):
        raise RuntimeError(
            "Star Rating의 채워진 별 수가 "
            "Recommendation Strength와 다릅니다."
        )

    if filled_stars + empty_stars != 5:
        raise RuntimeError(
            "Star Rating의 전체 별 수가 5가 아닙니다."
        )

    if (
        result.decision == "APPLY_CANDIDATE"
        and result.score_improvement < 3.0
    ):
        raise RuntimeError(
            "APPLY_CANDIDATE인데 기준 전략 대비 "
            "점수 개선이 3점 미만입니다."
        )

    if (
        result.decision
        == "PAPER_TRADE_CANDIDATE"
        and result.score_improvement <= 0.0
    ):
        raise RuntimeError(
            "PAPER_TRADE_CANDIDATE인데 기준 전략 대비 "
            "점수 개선이 없습니다."
        )

    if (
        result.decision == "KEEP_BASELINE"
        and result.selected_candidate_score
        > result.baseline_score
    ):
        raise RuntimeError(
            "KEEP_BASELINE인데 후보 점수가 "
            "기준 전략보다 높습니다."
        )

    if (
        not result.passed_all_checks
        and result.decision
        in {
            "APPLY_CANDIDATE",
            "PAPER_TRADE_CANDIDATE",
        }
    ):
        raise RuntimeError(
            "모든 품질 검사를 통과하지 못한 후보가 "
            "적용 또는 모의투자 대상으로 선택됐습니다."
        )


def validate_current_expected_result(
    result: FinalCandidateRecommendation,
) -> None:
    """
    현재 AAPL V8.3 결과에 따른 예상 판단을 검사합니다.

    현재 V8.3 결과에서는 후보 점수가 기준 전략보다
    낮으므로 KEEP_BASELINE이 정상입니다.
    """

    if result.score_improvement < 0.0:
        if result.decision != "KEEP_BASELINE":
            raise RuntimeError(
                "후보 점수가 기준 전략보다 낮지만 "
                "Decision이 KEEP_BASELINE이 아닙니다."
            )

        if not result.concerns:
            raise RuntimeError(
                "기준 전략보다 낮은 후보인데 "
                "Concerns가 생성되지 않았습니다."
            )

        improvement_concern_exists = any(
            (
                "기준 전략보다"
                in str(concern)
            )
            and (
                "낮습니다"
                in str(concern)
            )
            for concern in result.concerns
        )

        if not improvement_concern_exists:
            raise RuntimeError(
                "후보 점수가 기준 전략보다 낮다는 "
                "Concern이 없습니다."
            )

        baseline_action_exists = any(
            "기준 전략" in str(action)
            for action in result.required_actions
        )

        if not baseline_action_exists:
            raise RuntimeError(
                "KEEP_BASELINE 결정에 필요한 "
                "기준 전략 유지 작업이 없습니다."
            )


def validate_saved_files(
    result: FinalCandidateRecommendation,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.4 JSON 저장 결과와 내용을 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            f"시간별 V8.4 보고서가 없습니다: "
            f"{report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            f"V8.4 Latest 보고서가 없습니다: "
            f"{latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 V8.4 보고서가 비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "V8.4 Latest 보고서가 비어 있습니다."
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "시간별 보고서와 Latest 보고서 내용이 "
            "일치하지 않습니다."
        )

    required_json_keys = {
        "version",
        "symbol",
        "created_at",
        "source_file",
        "decision",
        "decision_label",
        "confidence_score",
        "confidence_level",
        "risk_score",
        "risk_level",
        "baseline_score",
        "selected_candidate_number",
        "selected_candidate_name",
        "selected_candidate_type",
        "selected_candidate_status",
        "selected_candidate_score",
        "score_improvement",
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
        "strategy_return_percent",
        "sharpe_ratio",
        "maximum_drawdown_percent",
        "profit_factor",
        "win_rate_percent",
        "total_trades",
        "walk_forward_status",
        "walk_forward_score",
        "profitable_windows_percent",
        "acceptable_windows_percent",
        "beat_default_return_percent",
        "parameter_stability_score",
        "backtest_success",
        "walk_forward_success",
        "passed_all_checks",
        "recommendation_strength",
        "reasons",
        "concerns",
        "required_actions",
        "report_path",
        "latest_path",
    }

    missing_keys = (
        required_json_keys
        - set(report_payload.keys())
    )

    if missing_keys:
        raise RuntimeError(
            "저장된 V8.4 JSON에 필수 키가 없습니다: "
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
        str(report_payload["decision"])
        != result.decision
    ):
        raise RuntimeError(
            "저장된 Decision이 실행 결과와 "
            "일치하지 않습니다."
        )

    if (
        str(
            report_payload[
                "selected_candidate_name"
            ]
        )
        != result.selected_candidate_name
    ):
        raise RuntimeError(
            "저장된 Candidate Name이 실행 결과와 "
            "일치하지 않습니다."
        )

    if abs(
        safe_float(
            report_payload[
                "selected_candidate_score"
            ]
        )
        - result.selected_candidate_score
    ) > 0.01:
        raise RuntimeError(
            "저장된 Candidate Score가 실행 결과와 "
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
        safe_int(
            report_payload[
                "recommendation_strength"
            ]
        )
        != result.recommendation_strength
    ):
        raise RuntimeError(
            "저장된 Recommendation Strength가 "
            "실행 결과와 일치하지 않습니다."
        )

    if (
        Path(
            str(
                report_payload[
                    "report_path"
                ]
            )
        )
        != report_path
    ):
        raise RuntimeError(
            "저장된 Report Path가 실제 경로와 "
            "일치하지 않습니다."
        )

    if (
        Path(
            str(
                report_payload[
                    "latest_path"
                ]
            )
        )
        != latest_path
    ):
        raise RuntimeError(
            "저장된 Latest Path가 실제 경로와 "
            "일치하지 않습니다."
        )


def print_validation_checks(
    result: FinalCandidateRecommendation,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    테스트 검증 결과를 보기 쉽게 출력합니다.
    """

    expected_improvement = round(
        result.selected_candidate_score
        - result.baseline_score,
        2,
    )

    expected_decision = calculate_expected_decision(
        result
    )

    expected_confidence_level = (
        calculate_expected_confidence_level(
            result.confidence_score
        )
    )

    expected_risk_level = (
        calculate_expected_risk_level(
            result.risk_score
        )
    )

    source_exists = Path(
        result.source_file
    ).exists()

    report_exists = report_path.exists()
    latest_exists = latest_path.exists()

    score_improvement_matches = (
        abs(
            expected_improvement
            - result.score_improvement
        )
        <= 0.01
    )

    decision_matches = (
        expected_decision
        == result.decision
    )

    confidence_level_matches = (
        expected_confidence_level
        == result.confidence_level
    )

    risk_level_matches = (
        expected_risk_level
        == result.risk_level
    )

    strength_valid = (
        1
        <= result.recommendation_strength
        <= 5
    )

    required_actions_exist = bool(
        result.required_actions
    )

    print()
    print("=" * 130)
    print("VALIDATION CHECKS")
    print("=" * 130)

    print(
        f"Version is V8.4                  : "
        f"{result.version == 'V8.4'}"
    )

    print(
        f"Source file exists               : "
        f"{source_exists}"
    )

    print(
        f"Decision is valid                : "
        f"{result.decision in VALID_DECISIONS}"
    )

    print(
        f"Confidence score is valid        : "
        f"{0.0 <= result.confidence_score <= 100.0}"
    )

    print(
        f"Confidence level matches         : "
        f"{confidence_level_matches}"
    )

    print(
        f"Risk score is valid              : "
        f"{0.0 <= result.risk_score <= 100.0}"
    )

    print(
        f"Risk level matches               : "
        f"{risk_level_matches}"
    )

    print(
        f"Score improvement matches        : "
        f"{score_improvement_matches}"
    )

    print(
        f"Final decision matches rules     : "
        f"{decision_matches}"
    )

    print(
        f"Recommendation strength valid    : "
        f"{strength_valid}"
    )

    print(
        f"Candidate parameters exist       : "
        f"{all([
            result.entry_score is not None,
            result.exit_score is not None,
            result.stop_atr_multiple is not None,
            result.target_atr_multiple is not None,
            result.maximum_holding_days is not None,
            result.position_percent is not None,
        ])}"
    )

    print(
        f"Required actions exist            : "
        f"{required_actions_exist}"
    )

    print(
        f"Report file exists               : "
        f"{report_exists}"
    )

    print(
        f"Latest file exists               : "
        f"{latest_exists}"
    )

    print("=" * 130)


def print_test_result(
    result: FinalCandidateRecommendation,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.4 테스트 결과를 요약하여 출력합니다.
    """

    print()
    print("=" * 130)
    print(
        "V8.4 FINAL CANDIDATE "
        "RECOMMENDER TEST RESULT"
    )
    print("=" * 130)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

    print(
        f"Decision                       : "
        f"{result.decision}"
    )

    print(
        f"Decision label                 : "
        f"{result.decision_label}"
    )

    print(
        f"Recommendation strength        : "
        f"{build_star_rating(result.recommendation_strength)}"
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

    print()
    print("SCORE COMPARISON")
    print("-" * 130)

    print(
        f"Baseline score                 : "
        f"{result.baseline_score:.2f}/100"
    )

    print(
        f"Candidate score                : "
        f"{result.selected_candidate_score:.2f}/100"
    )

    print(
        f"Score improvement              : "
        f"{result.score_improvement:+.2f} points"
    )

    print()
    print("SELECTED CANDIDATE")
    print("-" * 130)

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

    print(
        f"Candidate status               : "
        f"{result.selected_candidate_status}"
    )

    print()
    print("PARAMETERS")
    print("-" * 130)

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
    print("PERFORMANCE")
    print("-" * 130)

    print(
        f"Strategy return                : "
        f"{result.strategy_return_percent:.2f}%"
    )

    print(
        f"Sharpe ratio                   : "
        f"{result.sharpe_ratio:.2f}"
    )

    print(
        f"Maximum drawdown               : "
        f"{result.maximum_drawdown_percent:.2f}%"
    )

    print(
        f"Profit factor                  : "
        f"{result.profit_factor:.2f}"
    )

    print(
        f"Win rate                       : "
        f"{result.win_rate_percent:.2f}%"
    )

    print(
        f"Total trades                   : "
        f"{result.total_trades}"
    )

    print()
    print("WALK-FORWARD")
    print("-" * 130)

    print(
        f"Walk-Forward status            : "
        f"{result.walk_forward_status}"
    )

    print(
        f"Walk-Forward score             : "
        f"{result.walk_forward_score:.2f}/100"
    )

    print(
        f"Profitable windows             : "
        f"{result.profitable_windows_percent:.2f}%"
    )

    print(
        f"Acceptable windows             : "
        f"{result.acceptable_windows_percent:.2f}%"
    )

    print(
        f"Beat default return            : "
        f"{result.beat_default_return_percent:.2f}%"
    )

    print(
        f"Parameter stability            : "
        f"{result.parameter_stability_score:.2f}/100"
    )

    print()
    print("FILES")
    print("-" * 130)

    print(
        f"Source file                    : "
        f"{result.source_file}"
    )

    print(
        f"Report file                    : "
        f"{report_path}"
    )

    print(
        f"Latest file                    : "
        f"{latest_path}"
    )

    print("=" * 130)


def main() -> None:
    """
    V8.4 Final Candidate Recommender 통합 테스트입니다.

    V8.3의 최종 후보 결과를 읽고 다음 항목을 검사합니다.

    1. 기준 전략과 후보 전략 점수 비교
    2. 신뢰도와 위험도 계산
    3. 최종 적용 여부 결정
    4. 추천 이유, 우려 사항 및 후속 작업 생성
    5. JSON 결과 저장
    6. 저장된 JSON 내용 검증
    """

    symbol = "AAPL"

    print_test_header()

    try:
        result = run_final_candidate_recommendation(
            symbol=symbol,
        )

        (
            report_path,
            latest_path,
        ) = save_final_candidate_recommendation(
            result
        )

        # 저장 경로가 반영된 최종 결과를
        # 다시 출력합니다.
        print_final_candidate_recommendation(
            result
        )

        validate_result_structure(
            result
        )

        validate_calculations(
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
            "V8.4 final candidate recommender "
            "test completed successfully."
        )

        if result.decision == "KEEP_BASELINE":
            print(
                "최종 후보가 품질 검사를 통과했지만 "
                "기준 전략 점수보다 낮아 기존 전략을 "
                "유지하도록 정상 판단했습니다."
            )

        elif result.decision == "APPLY_CANDIDATE":
            print(
                "후보 전략이 기준 전략보다 충분히 "
                "개선되어 적용 후보로 정상 판단했습니다."
            )

        elif (
            result.decision
            == "PAPER_TRADE_CANDIDATE"
        ):
            print(
                "후보 전략이 개선 가능성을 보였지만 "
                "즉시 적용하지 않고 모의투자 대상으로 "
                "정상 판단했습니다."
            )

        else:
            print(
                "후보 전략을 실제 운영에 적용하지 않고 "
                "추가 연구 대상으로 정상 판단했습니다."
            )

        print(
            "주의: 이 결과는 과거 데이터 기반 연구용 "
            "판단이며 실제 투자 조언, 자동 주문 지시 "
            "또는 미래 수익 보장이 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 130)
        print("TEST CANCELLED")
        print("=" * 130)

        print(
            "사용자가 V8.4 Final Candidate "
            "Recommender 테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 130)
        print(
            "V8.4 FINAL CANDIDATE "
            "RECOMMENDER ERROR"
        )
        print("=" * 130)

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