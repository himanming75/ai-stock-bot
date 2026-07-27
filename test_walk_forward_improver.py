from pathlib import Path
from typing import Any

from backtest.walk_forward_improver import (
    WalkForwardImprovementResult,
    print_walk_forward_improvement,
    run_walk_forward_improvement_generator,
    save_walk_forward_improvement,
)


VALID_CANDIDATE_TYPES = {
    "CONSERVATIVE",
    "BALANCED",
    "AGGRESSIVE",
}

VALID_PRIORITY_STATUSES = {
    "HIGH_PRIORITY",
    "MEDIUM_PRIORITY",
    "LOW_PRIORITY",
}

VALID_RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
}

VALID_SELECTIVITY_LEVELS = {
    "LOW",
    "MEDIUM_LOW",
    "MEDIUM",
    "HIGH",
    "VERY_HIGH",
}

VALID_FREQUENCY_LEVELS = {
    "LOW",
    "MEDIUM_LOW",
    "MEDIUM",
    "MEDIUM_HIGH",
    "HIGH",
}


def print_test_header() -> None:
    """
    V8.2 Walk-Forward Improvement Generator
    테스트 제목을 출력합니다.
    """

    print()
    print("=" * 150)
    print(
        "AI STOCK BOT V8.2 "
        "WALK-FORWARD IMPROVEMENT GENERATOR TEST"
    )
    print("=" * 150)


def format_optional_value(
    value: Any,
) -> str:
    """
    None을 포함한 값을 출력용 문자열로 변환합니다.
    """

    if value is None:
        return "N/A"

    if isinstance(value, float):
        return f"{value:.2f}"

    return str(value)


def print_candidate_details(
    result: WalkForwardImprovementResult,
) -> None:
    """
    생성된 모든 개선 후보의 상세 내용을 출력합니다.
    """

    print()
    print("=" * 150)
    print("IMPROVEMENT CANDIDATE DETAILS")
    print("=" * 150)

    for candidate in result.candidates:
        candidate_number = int(
            candidate["candidate_number"]
        )

        print()
        print("-" * 150)

        print(
            f"CANDIDATE "
            f"{candidate_number}/"
            f"{result.total_candidates}"
        )

        print("-" * 150)

        print(
            f"Candidate name               : "
            f"{candidate['candidate_name']}"
        )

        print(
            f"Candidate type               : "
            f"{candidate['candidate_type']}"
        )

        print(
            f"Recommendation status        : "
            f"{candidate['recommendation_status']}"
        )

        print(
            f"Priority score               : "
            f"{float(candidate['priority_score']):.2f}/100"
        )

        print()
        print("PARAMETERS")
        print("-" * 150)

        print(
            f"Entry score                  : "
            f"{float(candidate['entry_score']):.2f}"
        )

        print(
            f"Exit score                   : "
            f"{float(candidate['exit_score']):.2f}"
        )

        print(
            f"Stop ATR                     : "
            f"{float(candidate['stop_atr_multiple']):.2f}"
        )

        print(
            f"Target ATR                   : "
            f"{float(candidate['target_atr_multiple']):.2f}"
        )

        print(
            f"Maximum holding days         : "
            f"{int(candidate['maximum_holding_days'])}"
        )

        print(
            f"Position percent             : "
            f"{float(candidate['position_percent']):.2f}%"
        )

        print()
        print("CHANGES FROM BASELINE")
        print("-" * 150)

        print(
            f"Entry change                 : "
            f"{float(candidate['entry_change']):+.2f}"
        )

        print(
            f"Exit change                  : "
            f"{float(candidate['exit_change']):+.2f}"
        )

        print(
            f"Stop ATR change              : "
            f"{float(candidate['stop_atr_change']):+.2f}"
        )

        print(
            f"Target ATR change            : "
            f"{float(candidate['target_atr_change']):+.2f}"
        )

        print(
            f"Holding days change          : "
            f"{int(candidate['holding_days_change']):+d}"
        )

        print(
            f"Position percent change      : "
            f"{float(candidate['position_percent_change']):+.2f}%p"
        )

        print()
        print("ESTIMATED CHARACTERISTICS")
        print("-" * 150)

        print(
            f"Estimated selectivity        : "
            f"{candidate['estimated_selectivity']}"
        )

        print(
            f"Estimated trade frequency    : "
            f"{candidate['estimated_trade_frequency']}"
        )

        print(
            f"Estimated risk level         : "
            f"{candidate['estimated_risk_level']}"
        )

        reasons = candidate.get(
            "reasons",
            [],
        )

        if reasons:
            print()
            print("REASONS")
            print("-" * 150)

            for reason in reasons:
                print(f"- {reason}")

        warnings = candidate.get(
            "warnings",
            [],
        )

        if warnings:
            print()
            print("WARNINGS")
            print("-" * 150)

            for warning in warnings:
                print(f"- {warning}")


def print_test_summary(
    result: WalkForwardImprovementResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.2 테스트 결과의 핵심 내용을 출력합니다.
    """

    print()
    print("=" * 150)
    print(
        "V8.2 WALK-FORWARD IMPROVEMENT "
        "GENERATOR TEST RESULT"
    )
    print("=" * 150)

    print(
        f"Symbol                        : "
        f"{result.symbol}"
    )

    print(
        f"Source file                   : "
        f"{result.source_file}"
    )

    print(
        f"Diagnostic status             : "
        f"{result.diagnostic_status}"
    )

    print(
        f"Diagnostic score              : "
        f"{result.diagnostic_score:.2f}/100"
    )

    print(
        f"Recent trend                  : "
        f"{result.recent_trend}"
    )

    print(
        f"Overfitting warning           : "
        f"{result.overfitting_warning}"
    )

    print(
        f"Elapsed time                  : "
        f"{result.elapsed_seconds:.2f} seconds"
    )

    print()
    print("BASE PARAMETERS")
    print("-" * 150)

    print(
        f"Base entry score              : "
        f"{result.base_entry_score:.2f}"
    )

    print(
        f"Base exit score               : "
        f"{result.base_exit_score:.2f}"
    )

    print(
        f"Base stop ATR                 : "
        f"{result.base_stop_atr:.2f}"
    )

    print(
        f"Base target ATR               : "
        f"{result.base_target_atr:.2f}"
    )

    print(
        f"Base holding days             : "
        f"{result.base_holding_days}"
    )

    print(
        f"Base position percent         : "
        f"{result.base_position_percent:.2f}%"
    )

    print()
    print("CANDIDATE COUNTS")
    print("-" * 150)

    print(
        f"Total candidates              : "
        f"{result.total_candidates}"
    )

    print(
        f"Conservative candidates       : "
        f"{result.conservative_candidates}"
    )

    print(
        f"Balanced candidates           : "
        f"{result.balanced_candidates}"
    )

    print(
        f"Aggressive candidates         : "
        f"{result.aggressive_candidates}"
    )

    print(
        f"High-priority candidates      : "
        f"{result.high_priority_candidates}"
    )

    print(
        f"Medium-priority candidates    : "
        f"{result.medium_priority_candidates}"
    )

    print(
        f"Low-priority candidates       : "
        f"{result.low_priority_candidates}"
    )

    print()
    print("RECOMMENDED CANDIDATE")
    print("-" * 150)

    print(
        f"Recommended candidate number  : "
        f"{format_optional_value(result.recommended_candidate_number)}"
    )

    print(
        f"Recommended candidate name    : "
        f"{format_optional_value(result.recommended_candidate_name)}"
    )

    print(
        f"Recommended priority score    : "
        f"{result.recommended_priority_score:.2f}/100"
    )

    recommended_candidate = find_recommended_candidate(
        result
    )

    if recommended_candidate is not None:
        print(
            f"Recommended candidate type    : "
            f"{recommended_candidate['candidate_type']}"
        )

        print(
            f"Recommended entry score       : "
            f"{float(recommended_candidate['entry_score']):.2f}"
        )

        print(
            f"Recommended exit score        : "
            f"{float(recommended_candidate['exit_score']):.2f}"
        )

        print(
            f"Recommended stop ATR          : "
            f"{float(recommended_candidate['stop_atr_multiple']):.2f}"
        )

        print(
            f"Recommended target ATR        : "
            f"{float(recommended_candidate['target_atr_multiple']):.2f}"
        )

        print(
            f"Recommended holding days      : "
            f"{int(recommended_candidate['maximum_holding_days'])}"
        )

        print(
            f"Recommended position percent  : "
            f"{float(recommended_candidate['position_percent']):.2f}%"
        )

        print(
            f"Estimated risk level          : "
            f"{recommended_candidate['estimated_risk_level']}"
        )

    print()
    print("VALIDATION CHECKS")
    print("-" * 150)

    candidate_count_matches = (
        len(result.candidates)
        == result.total_candidates
    )

    type_count_matches = (
        result.conservative_candidates
        + result.balanced_candidates
        + result.aggressive_candidates
        == result.total_candidates
    )

    priority_count_matches = (
        result.high_priority_candidates
        + result.medium_priority_candidates
        + result.low_priority_candidates
        == result.total_candidates
    )

    candidate_numbers_are_unique = (
        len(
            {
                int(candidate["candidate_number"])
                for candidate in result.candidates
            }
        )
        == result.total_candidates
    )

    candidate_names_are_unique = (
        len(
            {
                str(candidate["candidate_name"])
                for candidate in result.candidates
            }
        )
        == result.total_candidates
    )

    candidates_are_ranked = (
        check_candidate_ranking(result)
    )

    recommended_candidate_exists = (
        recommended_candidate is not None
    )

    recommended_score_matches = (
        recommended_candidate is not None
        and abs(
            float(recommended_candidate["priority_score"])
            - result.recommended_priority_score
        )
        <= 0.01
    )

    print(
        f"Candidate count matches       : "
        f"{candidate_count_matches}"
    )

    print(
        f"Type count matches            : "
        f"{type_count_matches}"
    )

    print(
        f"Priority count matches        : "
        f"{priority_count_matches}"
    )

    print(
        f"Candidate numbers unique      : "
        f"{candidate_numbers_are_unique}"
    )

    print(
        f"Candidate names unique        : "
        f"{candidate_names_are_unique}"
    )

    print(
        f"Candidates correctly ranked   : "
        f"{candidates_are_ranked}"
    )

    print(
        f"Recommended candidate exists  : "
        f"{recommended_candidate_exists}"
    )

    print(
        f"Recommended score matches     : "
        f"{recommended_score_matches}"
    )

    print()
    print("FILES")
    print("-" * 150)

    print(
        f"Report file                   : "
        f"{report_path}"
    )

    print(
        f"Latest file                   : "
        f"{latest_path}"
    )

    print("=" * 150)


def find_recommended_candidate(
    result: WalkForwardImprovementResult,
) -> dict[str, Any] | None:
    """
    결과 목록에서 최종 추천 후보를 찾습니다.
    """

    recommended_number = (
        result.recommended_candidate_number
    )

    recommended_name = (
        result.recommended_candidate_name
    )

    for candidate in result.candidates:
        number_matches = (
            recommended_number is not None
            and int(candidate["candidate_number"])
            == recommended_number
        )

        name_matches = (
            recommended_name is not None
            and str(candidate["candidate_name"])
            == recommended_name
        )

        if number_matches and name_matches:
            return candidate

    return None


def check_candidate_ranking(
    result: WalkForwardImprovementResult,
) -> bool:
    """
    후보가 Priority Score 내림차순으로
    정렬되어 있는지 검사합니다.
    """

    priority_scores = [
        float(candidate["priority_score"])
        for candidate in result.candidates
    ]

    return priority_scores == sorted(
        priority_scores,
        reverse=True,
    )


def validate_candidate_structure(
    result: WalkForwardImprovementResult,
) -> None:
    """
    각 개선 후보의 필수 필드와 값 범위를 검사합니다.
    """

    required_keys = {
        "candidate_number",
        "candidate_name",
        "candidate_type",
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
        "entry_change",
        "exit_change",
        "stop_atr_change",
        "target_atr_change",
        "holding_days_change",
        "position_percent_change",
        "estimated_selectivity",
        "estimated_trade_frequency",
        "estimated_risk_level",
        "priority_score",
        "recommendation_status",
        "reasons",
        "warnings",
    }

    for candidate in result.candidates:
        candidate_number = int(
            candidate.get(
                "candidate_number",
                0,
            )
        )

        missing_keys = (
            required_keys
            - set(candidate.keys())
        )

        if missing_keys:
            raise RuntimeError(
                f"Candidate {candidate_number}에 "
                f"필수 키가 없습니다: "
                f"{sorted(missing_keys)}"
            )

        candidate_type = str(
            candidate["candidate_type"]
        )

        if candidate_type not in VALID_CANDIDATE_TYPES:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                f"Candidate Type이 올바르지 않습니다: "
                f"{candidate_type}"
            )

        recommendation_status = str(
            candidate["recommendation_status"]
        )

        if (
            recommendation_status
            not in VALID_PRIORITY_STATUSES
        ):
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Recommendation Status가 "
                f"올바르지 않습니다: "
                f"{recommendation_status}"
            )

        risk_level = str(
            candidate["estimated_risk_level"]
        )

        if risk_level not in VALID_RISK_LEVELS:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                f"Risk Level이 올바르지 않습니다: "
                f"{risk_level}"
            )

        selectivity = str(
            candidate["estimated_selectivity"]
        )

        if selectivity not in VALID_SELECTIVITY_LEVELS:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Selectivity 값이 올바르지 않습니다: "
                f"{selectivity}"
            )

        trade_frequency = str(
            candidate[
                "estimated_trade_frequency"
            ]
        )

        if (
            trade_frequency
            not in VALID_FREQUENCY_LEVELS
        ):
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Trade Frequency 값이 올바르지 않습니다: "
                f"{trade_frequency}"
            )

        priority_score = float(
            candidate["priority_score"]
        )

        if not 0.0 <= priority_score <= 100.0:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Priority Score가 0~100 범위를 "
                f"벗어났습니다: {priority_score:.2f}"
            )

        entry_score = float(
            candidate["entry_score"]
        )

        if not 50.0 <= entry_score <= 90.0:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Entry Score가 유효 범위를 "
                f"벗어났습니다: {entry_score:.2f}"
            )

        exit_score = float(
            candidate["exit_score"]
        )

        if not 20.0 <= exit_score <= 70.0:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Exit Score가 유효 범위를 "
                f"벗어났습니다: {exit_score:.2f}"
            )

        stop_atr = float(
            candidate["stop_atr_multiple"]
        )

        if not 0.75 <= stop_atr <= 3.0:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Stop ATR이 유효 범위를 "
                f"벗어났습니다: {stop_atr:.2f}"
            )

        target_atr = float(
            candidate["target_atr_multiple"]
        )

        if not 1.0 <= target_atr <= 5.0:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Target ATR이 유효 범위를 "
                f"벗어났습니다: {target_atr:.2f}"
            )

        holding_days = int(
            candidate["maximum_holding_days"]
        )

        if not 5 <= holding_days <= 60:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Holding Days가 유효 범위를 "
                f"벗어났습니다: {holding_days}"
            )

        position_percent = float(
            candidate["position_percent"]
        )

        if not 5.0 <= position_percent <= 30.0:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "Position Percent가 유효 범위를 "
                f"벗어났습니다: {position_percent:.2f}"
            )

        reasons = candidate["reasons"]
        warnings = candidate["warnings"]

        if not isinstance(reasons, list):
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "reasons가 목록이 아닙니다."
            )

        if not reasons:
            raise RuntimeError(
                f"Candidate {candidate_number}에 "
                "생성 이유가 없습니다."
            )

        if not isinstance(warnings, list):
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                "warnings가 목록이 아닙니다."
            )

        validate_candidate_changes(
            result=result,
            candidate=candidate,
        )


def validate_candidate_changes(
    result: WalkForwardImprovementResult,
    candidate: dict[str, Any],
) -> None:
    """
    후보 파라미터와 기준 파라미터의 차이가
    저장된 Change 값과 일치하는지 검사합니다.
    """

    candidate_number = int(
        candidate["candidate_number"]
    )

    expected_entry_change = round(
        float(candidate["entry_score"])
        - result.base_entry_score,
        2,
    )

    expected_exit_change = round(
        float(candidate["exit_score"])
        - result.base_exit_score,
        2,
    )

    expected_stop_change = round(
        float(candidate["stop_atr_multiple"])
        - result.base_stop_atr,
        2,
    )

    expected_target_change = round(
        float(candidate["target_atr_multiple"])
        - result.base_target_atr,
        2,
    )

    expected_holding_change = (
        int(candidate["maximum_holding_days"])
        - result.base_holding_days
    )

    expected_position_change = round(
        float(candidate["position_percent"])
        - result.base_position_percent,
        2,
    )

    comparisons = {
        "entry_change": (
            expected_entry_change,
            float(candidate["entry_change"]),
        ),
        "exit_change": (
            expected_exit_change,
            float(candidate["exit_change"]),
        ),
        "stop_atr_change": (
            expected_stop_change,
            float(candidate["stop_atr_change"]),
        ),
        "target_atr_change": (
            expected_target_change,
            float(candidate["target_atr_change"]),
        ),
        "position_percent_change": (
            expected_position_change,
            float(
                candidate[
                    "position_percent_change"
                ]
            ),
        ),
    }

    for field_name, values in comparisons.items():
        expected_value, saved_value = values

        if abs(expected_value - saved_value) > 0.01:
            raise RuntimeError(
                f"Candidate {candidate_number}의 "
                f"{field_name} 계산이 일치하지 않습니다. "
                f"Expected={expected_value:.2f}, "
                f"Saved={saved_value:.2f}"
            )

    saved_holding_change = int(
        candidate["holding_days_change"]
    )

    if expected_holding_change != saved_holding_change:
        raise RuntimeError(
            f"Candidate {candidate_number}의 "
            "holding_days_change 계산이 "
            "일치하지 않습니다. "
            f"Expected={expected_holding_change}, "
            f"Saved={saved_holding_change}"
        )


def validate_result_structure(
    result: WalkForwardImprovementResult,
) -> None:
    """
    V8.2 전체 결과의 집계 및 추천 후보를 검사합니다.
    """

    if result.total_candidates <= 0:
        raise RuntimeError(
            "생성된 개선 후보가 없습니다."
        )

    if len(result.candidates) != result.total_candidates:
        raise RuntimeError(
            "Candidate 목록 길이와 "
            "Total Candidates가 일치하지 않습니다."
        )

    type_count = (
        result.conservative_candidates
        + result.balanced_candidates
        + result.aggressive_candidates
    )

    if type_count != result.total_candidates:
        raise RuntimeError(
            "후보 유형별 개수의 합계가 "
            "Total Candidates와 다릅니다."
        )

    priority_count = (
        result.high_priority_candidates
        + result.medium_priority_candidates
        + result.low_priority_candidates
    )

    if priority_count != result.total_candidates:
        raise RuntimeError(
            "후보 우선순위별 개수의 합계가 "
            "Total Candidates와 다릅니다."
        )

    calculated_conservative = sum(
        1
        for candidate in result.candidates
        if candidate["candidate_type"]
        == "CONSERVATIVE"
    )

    calculated_balanced = sum(
        1
        for candidate in result.candidates
        if candidate["candidate_type"]
        == "BALANCED"
    )

    calculated_aggressive = sum(
        1
        for candidate in result.candidates
        if candidate["candidate_type"]
        == "AGGRESSIVE"
    )

    if (
        calculated_conservative
        != result.conservative_candidates
    ):
        raise RuntimeError(
            "Conservative Candidate 집계가 "
            "일치하지 않습니다."
        )

    if calculated_balanced != result.balanced_candidates:
        raise RuntimeError(
            "Balanced Candidate 집계가 "
            "일치하지 않습니다."
        )

    if calculated_aggressive != result.aggressive_candidates:
        raise RuntimeError(
            "Aggressive Candidate 집계가 "
            "일치하지 않습니다."
        )

    calculated_high_priority = sum(
        1
        for candidate in result.candidates
        if candidate["recommendation_status"]
        == "HIGH_PRIORITY"
    )

    calculated_medium_priority = sum(
        1
        for candidate in result.candidates
        if candidate["recommendation_status"]
        == "MEDIUM_PRIORITY"
    )

    calculated_low_priority = sum(
        1
        for candidate in result.candidates
        if candidate["recommendation_status"]
        == "LOW_PRIORITY"
    )

    if (
        calculated_high_priority
        != result.high_priority_candidates
    ):
        raise RuntimeError(
            "High-Priority Candidate 집계가 "
            "일치하지 않습니다."
        )

    if (
        calculated_medium_priority
        != result.medium_priority_candidates
    ):
        raise RuntimeError(
            "Medium-Priority Candidate 집계가 "
            "일치하지 않습니다."
        )

    if (
        calculated_low_priority
        != result.low_priority_candidates
    ):
        raise RuntimeError(
            "Low-Priority Candidate 집계가 "
            "일치하지 않습니다."
        )

    candidate_numbers = [
        int(candidate["candidate_number"])
        for candidate in result.candidates
    ]

    expected_numbers = list(
        range(
            1,
            result.total_candidates + 1,
        )
    )

    if candidate_numbers != expected_numbers:
        raise RuntimeError(
            "Candidate Number가 1부터 연속적으로 "
            "정렬되어 있지 않습니다."
        )

    if not check_candidate_ranking(result):
        raise RuntimeError(
            "후보가 Priority Score 내림차순으로 "
            "정렬되어 있지 않습니다."
        )

    top_candidate = result.candidates[0]

    if (
        result.recommended_candidate_number
        != int(top_candidate["candidate_number"])
    ):
        raise RuntimeError(
            "Recommended Candidate Number가 "
            "최상위 후보와 다릅니다."
        )

    if (
        result.recommended_candidate_name
        != str(top_candidate["candidate_name"])
    ):
        raise RuntimeError(
            "Recommended Candidate Name이 "
            "최상위 후보와 다릅니다."
        )

    if abs(
        result.recommended_priority_score
        - float(top_candidate["priority_score"])
    ) > 0.01:
        raise RuntimeError(
            "Recommended Priority Score가 "
            "최상위 후보 점수와 다릅니다."
        )

    if not 0.0 <= result.diagnostic_score <= 100.0:
        raise RuntimeError(
            "Diagnostic Score가 0~100 범위를 "
            f"벗어났습니다: {result.diagnostic_score:.2f}"
        )

    if not (
        0.0
        <= result.recommended_priority_score
        <= 100.0
    ):
        raise RuntimeError(
            "Recommended Priority Score가 "
            "0~100 범위를 벗어났습니다."
        )

    validate_candidate_structure(result)


def validate_saved_files(
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.2 JSON 결과 파일의 생성 여부를 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            "시간별 Walk-Forward Improvement "
            f"보고서가 생성되지 않았습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            "Latest Walk-Forward Improvement "
            f"보고서가 생성되지 않았습니다: {latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 Walk-Forward Improvement "
            "보고서가 비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "Latest Walk-Forward Improvement "
            "보고서가 비어 있습니다."
        )


def main() -> None:
    """
    V8.2 Walk-Forward Improvement Generator
    통합 테스트입니다.

    V8.1 Walk-Forward Diagnostic 결과를 읽고
    기준 파라미터 주변의 개선 후보를 생성한 후
    후보 분류, 우선순위, 위험 수준 및 저장 결과를
    자동 검사합니다.
    """

    symbol = "AAPL"
    maximum_candidates = 30

    print_test_header()

    try:
        result = (
            run_walk_forward_improvement_generator(
                symbol=symbol,
                maximum_candidates=maximum_candidates,
            )
        )

        (
            report_path,
            latest_path,
        ) = save_walk_forward_improvement(
            result
        )

        print_walk_forward_improvement(
            result
        )

        print_candidate_details(
            result
        )

        print_test_summary(
            result=result,
            report_path=report_path,
            latest_path=latest_path,
        )

        validate_result_structure(
            result
        )

        validate_saved_files(
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V8.2 walk-forward improvement "
            "generator test completed successfully."
        )

        print(
            "V8.1 진단 결과를 기반으로 "
            "Walk-Forward 개선 후보 파라미터를 "
            "정상적으로 생성했습니다."
        )

        print(
            "주의: 생성된 후보는 아직 실제 성능이 "
            "검증되지 않은 연구용 파라미터입니다. "
            "다음 단계에서 별도의 Walk-Forward "
            "백테스트로 비교해야 합니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 150)
        print("TEST CANCELLED")
        print("=" * 150)

        print(
            "사용자가 V8.2 Walk-Forward Improvement "
            "Generator 테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 150)
        print(
            "V8.2 WALK-FORWARD IMPROVEMENT "
            "GENERATOR ERROR"
        )
        print("=" * 150)

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