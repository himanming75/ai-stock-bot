from pathlib import Path
from typing import Any

from backtest.improvement_candidate_backtester import (
    ImprovementCandidateBacktestReport,
    print_improvement_candidate_backtest,
    run_improvement_candidate_backtest,
    save_improvement_candidate_backtest,
)


VALID_CANDIDATE_TYPES = {
    "CONSERVATIVE",
    "BALANCED",
    "AGGRESSIVE",
    "BASELINE",
    "UNKNOWN",
}

VALID_FINAL_STATUSES = {
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
    V8.3 Improvement Candidate Backtester
    테스트 제목을 출력합니다.
    """

    print()
    print("=" * 160)
    print(
        "AI STOCK BOT V8.3 "
        "IMPROVEMENT CANDIDATE BACKTESTER TEST"
    )
    print("=" * 160)


def format_optional_value(
    value: Any,
    decimal_places: int = 2,
) -> str:
    """
    None을 포함한 값을 출력용 문자열로 변환합니다.
    """

    if value is None:
        return "N/A"

    if isinstance(value, float):
        return f"{value:.{decimal_places}f}"

    return str(value)


def find_winner(
    report: ImprovementCandidateBacktestReport,
) -> dict[str, Any] | None:
    """
    결과 목록에서 최종 우승 후보를 찾습니다.
    """

    if not report.candidates:
        return None

    winner_name = report.winner_candidate_name
    winner_number = report.winner_candidate_number

    for candidate in report.candidates:
        name_matches = (
            winner_name is not None
            and str(candidate["candidate_name"])
            == winner_name
        )

        number_matches = (
            winner_number is not None
            and int(
                candidate["source_candidate_number"]
            )
            == winner_number
        )

        if name_matches and number_matches:
            return candidate

    return None


def check_candidate_ranking(
    report: ImprovementCandidateBacktestReport,
) -> bool:
    """
    후보들이 통과 여부와 최종 점수를 기준으로
    올바르게 정렬되었는지 검사합니다.
    """

    expected = sorted(
        report.candidates,
        key=lambda candidate: (
            bool(
                candidate["passed_all_checks"]
            ),
            float(
                candidate["final_score"]
            ),
            float(
                candidate[
                    "walk_forward_component_score"
                ]
            ),
            float(
                candidate["sharpe_ratio"]
            ),
            float(
                candidate[
                    "strategy_return_percent"
                ]
            ),
            -abs(
                float(
                    candidate[
                        "maximum_drawdown_percent"
                    ]
                )
            ),
        ),
        reverse=True,
    )

    actual_identity = [
        (
            int(candidate["rank"]),
            int(
                candidate[
                    "source_candidate_number"
                ]
            ),
            str(candidate["candidate_name"]),
        )
        for candidate in report.candidates
    ]

    expected_identity = [
        (
            index,
            int(
                candidate[
                    "source_candidate_number"
                ]
            ),
            str(candidate["candidate_name"]),
        )
        for index, candidate in enumerate(
            expected,
            start=1,
        )
    ]

    return actual_identity == expected_identity


def print_candidate_details(
    report: ImprovementCandidateBacktestReport,
) -> None:
    """
    테스트된 각 개선 후보의 상세 결과를 출력합니다.
    """

    print()
    print("=" * 160)
    print("CANDIDATE BACKTEST DETAILS")
    print("=" * 160)

    for candidate in report.candidates:
        rank = int(
            candidate["rank"]
        )

        print()
        print("-" * 160)

        print(
            f"RANK {rank}/"
            f"{report.tested_candidates}"
        )

        print("-" * 160)

        print(
            f"Source candidate number      : "
            f"{candidate['source_candidate_number']}"
        )

        print(
            f"Candidate name               : "
            f"{candidate['candidate_name']}"
        )

        print(
            f"Candidate type               : "
            f"{candidate['candidate_type']}"
        )

        print(
            f"Generator priority           : "
            f"{float(candidate['generator_priority_score']):.2f}/100"
        )

        print(
            f"Generator status             : "
            f"{candidate['recommendation_status']}"
        )

        print()
        print("PARAMETERS")
        print("-" * 160)

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
        print("BACKTEST PERFORMANCE")
        print("-" * 160)

        print(
            f"Backtest success             : "
            f"{candidate['backtest_success']}"
        )

        print(
            f"Strategy return              : "
            f"{float(candidate['strategy_return_percent']):.2f}%"
        )

        print(
            f"Buy and hold return          : "
            f"{float(candidate['buy_and_hold_return_percent']):.2f}%"
        )

        print(
            f"Excess return                : "
            f"{float(candidate['excess_return_percent']):.2f}%p"
        )

        print(
            f"Sharpe ratio                 : "
            f"{float(candidate['sharpe_ratio']):.2f}"
        )

        print(
            f"Maximum drawdown             : "
            f"{float(candidate['maximum_drawdown_percent']):.2f}%"
        )

        print(
            f"Profit factor                : "
            f"{float(candidate['profit_factor']):.2f}"
        )

        print(
            f"Win rate                     : "
            f"{float(candidate['win_rate_percent']):.2f}%"
        )

        print(
            f"Total trades                 : "
            f"{int(candidate['total_trades'])}"
        )

        print()
        print("WALK-FORWARD PERFORMANCE")
        print("-" * 160)

        print(
            f"Walk-Forward success         : "
            f"{candidate['walk_forward_success']}"
        )

        print(
            f"Walk-Forward status          : "
            f"{candidate['walk_forward_status']}"
        )

        print(
            f"Walk-Forward source score    : "
            f"{float(candidate['walk_forward_score']):.2f}/100"
        )

        print(
            f"Profitable windows           : "
            f"{float(candidate['profitable_windows_percent']):.2f}%"
        )

        print(
            f"Acceptable windows           : "
            f"{float(candidate['acceptable_windows_percent']):.2f}%"
        )

        print(
            f"Beat default return          : "
            f"{float(candidate['beat_default_return_percent']):.2f}%"
        )

        print(
            f"Parameter stability          : "
            f"{float(candidate['parameter_stability_score']):.2f}/100"
        )

        print()
        print("COMPONENT SCORES")
        print("-" * 160)

        print(
            f"Return score                 : "
            f"{float(candidate['return_score']):.2f}/100"
        )

        print(
            f"Sharpe score                 : "
            f"{float(candidate['sharpe_score']):.2f}/100"
        )

        print(
            f"Drawdown score               : "
            f"{float(candidate['drawdown_score']):.2f}/100"
        )

        print(
            f"Profit factor score          : "
            f"{float(candidate['profit_factor_score']):.2f}/100"
        )

        print(
            f"Trade quality score          : "
            f"{float(candidate['trade_quality_score']):.2f}/100"
        )

        print(
            f"Walk-Forward component       : "
            f"{float(candidate['walk_forward_component_score']):.2f}/100"
        )

        print()
        print("FINAL EVALUATION")
        print("-" * 160)

        print(
            f"Final score                  : "
            f"{float(candidate['final_score']):.2f}/100"
        )

        print(
            f"Final status                 : "
            f"{candidate['final_status']}"
        )

        print()
        print("QUALITY CHECKS")
        print("-" * 160)

        print(
            f"Minimum trades passed        : "
            f"{candidate['passed_minimum_trades']}"
        )

        print(
            f"Drawdown limit passed        : "
            f"{candidate['passed_drawdown_limit']}"
        )

        print(
            f"Profit factor passed         : "
            f"{candidate['passed_profit_factor']}"
        )

        print(
            f"Sharpe passed                : "
            f"{candidate['passed_sharpe']}"
        )

        print(
            f"Walk-Forward passed          : "
            f"{candidate['passed_walk_forward']}"
        )

        print(
            f"All checks passed            : "
            f"{candidate['passed_all_checks']}"
        )

        reasons = candidate.get(
            "reasons",
            [],
        )

        if reasons:
            print()
            print("REASONS")
            print("-" * 160)

            for reason in reasons:
                print(
                    f"- {reason}"
                )

        warnings = candidate.get(
            "warnings",
            [],
        )

        if warnings:
            print()
            print("WARNINGS")
            print("-" * 160)

            for warning in warnings:
                print(
                    f"- {warning}"
                )

        error_message = candidate.get(
            "error_message"
        )

        if error_message:
            print()
            print("ERROR MESSAGE")
            print("-" * 160)

            print(
                error_message
            )


def print_test_summary(
    report: ImprovementCandidateBacktestReport,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.3 테스트 결과 요약과 검증 항목을 출력합니다.
    """

    winner = find_winner(
        report
    )

    print()
    print("=" * 160)
    print(
        "V8.3 IMPROVEMENT CANDIDATE "
        "BACKTESTER TEST RESULT"
    )
    print("=" * 160)

    print(
        f"Symbol                         : "
        f"{report.symbol}"
    )

    print(
        f"Source file                    : "
        f"{report.source_file}"
    )

    print(
        f"Requested candidates           : "
        f"{report.requested_candidates}"
    )

    print(
        f"Tested candidates              : "
        f"{report.tested_candidates}"
    )

    print(
        f"Successful candidates          : "
        f"{report.successful_candidates}"
    )

    print(
        f"Failed candidates              : "
        f"{report.failed_candidates}"
    )

    print(
        f"Passed candidates              : "
        f"{report.passed_candidates}"
    )

    print(
        f"Rejected candidates            : "
        f"{report.rejected_candidates}"
    )

    print(
        f"Elapsed time                   : "
        f"{report.elapsed_seconds:.2f} seconds"
    )

    print()
    print("BASELINE")
    print("-" * 160)

    print(
        f"Baseline tested                : "
        f"{report.baseline_tested}"
    )

    print(
        f"Baseline final score           : "
        f"{report.baseline_final_score:.2f}/100"
    )

    print()
    print("WINNER")
    print("-" * 160)

    print(
        f"Winner candidate number        : "
        f"{format_optional_value(report.winner_candidate_number)}"
    )

    print(
        f"Winner candidate name          : "
        f"{format_optional_value(report.winner_candidate_name)}"
    )

    print(
        f"Winner candidate type          : "
        f"{format_optional_value(report.winner_candidate_type)}"
    )

    print(
        f"Winner final score             : "
        f"{report.winner_final_score:.2f}/100"
    )

    print(
        f"Winner status                  : "
        f"{format_optional_value(report.winner_status)}"
    )

    print(
        f"Improvement over baseline      : "
        f"{report.improvement_over_baseline_score:+.2f} points"
    )

    print()
    print("WINNER PARAMETERS")
    print("-" * 160)

    print(
        f"Entry score                    : "
        f"{format_optional_value(report.winner_entry_score)}"
    )

    print(
        f"Exit score                     : "
        f"{format_optional_value(report.winner_exit_score)}"
    )

    print(
        f"Stop ATR                       : "
        f"{format_optional_value(report.winner_stop_atr)}"
    )

    print(
        f"Target ATR                     : "
        f"{format_optional_value(report.winner_target_atr)}"
    )

    print(
        f"Maximum holding days           : "
        f"{format_optional_value(report.winner_holding_days)}"
    )

    print(
        f"Position percent               : "
        f"{format_optional_value(report.winner_position_percent)}%"
    )

    print()
    print("WINNER PERFORMANCE")
    print("-" * 160)

    print(
        f"Strategy return                : "
        f"{report.winner_strategy_return_percent:.2f}%"
    )

    print(
        f"Sharpe ratio                   : "
        f"{report.winner_sharpe_ratio:.2f}"
    )

    print(
        f"Maximum drawdown               : "
        f"{report.winner_drawdown_percent:.2f}%"
    )

    print(
        f"Profit factor                  : "
        f"{report.winner_profit_factor:.2f}"
    )

    print(
        f"Total trades                   : "
        f"{report.winner_total_trades}"
    )

    print()
    print("VALIDATION CHECKS")
    print("-" * 160)

    tested_count_matches = (
        len(report.candidates)
        == report.tested_candidates
    )

    success_failure_count_matches = (
        report.successful_candidates
        + report.failed_candidates
        == report.tested_candidates
    )

    pass_reject_count_matches = (
        report.passed_candidates
        + report.rejected_candidates
        == report.tested_candidates
    )

    candidate_ranks_are_sequential = (
        [
            int(candidate["rank"])
            for candidate in report.candidates
        ]
        == list(
            range(
                1,
                report.tested_candidates + 1,
            )
        )
    )

    candidates_correctly_ranked = (
        check_candidate_ranking(
            report
        )
    )

    winner_exists = (
        winner is not None
    )

    winner_is_rank_one = (
        winner is not None
        and int(winner["rank"]) == 1
    )

    winner_score_matches = (
        winner is not None
        and abs(
            float(winner["final_score"])
            - report.winner_final_score
        )
        <= 0.01
    )

    baseline_improvement_matches = (
        abs(
            (
                report.winner_final_score
                - report.baseline_final_score
            )
            - report.improvement_over_baseline_score
        )
        <= 0.01
    )

    all_final_scores_valid = all(
        0.0
        <= float(candidate["final_score"])
        <= 100.0
        for candidate in report.candidates
    )

    all_component_scores_valid = all(
        all(
            0.0 <= float(candidate[field]) <= 100.0
            for field in (
                "return_score",
                "sharpe_score",
                "drawdown_score",
                "profit_factor_score",
                "trade_quality_score",
                "walk_forward_component_score",
            )
        )
        for candidate in report.candidates
    )

    print(
        f"Tested count matches           : "
        f"{tested_count_matches}"
    )

    print(
        f"Success/failure count matches  : "
        f"{success_failure_count_matches}"
    )

    print(
        f"Pass/reject count matches      : "
        f"{pass_reject_count_matches}"
    )

    print(
        f"Candidate ranks sequential     : "
        f"{candidate_ranks_are_sequential}"
    )

    print(
        f"Candidates correctly ranked    : "
        f"{candidates_correctly_ranked}"
    )

    print(
        f"Winner exists                  : "
        f"{winner_exists}"
    )

    print(
        f"Winner is rank one             : "
        f"{winner_is_rank_one}"
    )

    print(
        f"Winner score matches           : "
        f"{winner_score_matches}"
    )

    print(
        f"Baseline improvement matches   : "
        f"{baseline_improvement_matches}"
    )

    print(
        f"All final scores valid         : "
        f"{all_final_scores_valid}"
    )

    print(
        f"All component scores valid     : "
        f"{all_component_scores_valid}"
    )

    print()
    print("FILES")
    print("-" * 160)

    print(
        f"Report file                    : "
        f"{report_path}"
    )

    print(
        f"Latest file                    : "
        f"{latest_path}"
    )

    print("=" * 160)


def validate_candidate_structure(
    report: ImprovementCandidateBacktestReport,
) -> None:
    """
    각 후보 결과의 필수 필드와 값 범위를 검사합니다.
    """

    required_keys = {
        "rank",
        "source_candidate_number",
        "candidate_name",
        "candidate_type",
        "recommendation_status",
        "generator_priority_score",
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
        "backtest_success",
        "walk_forward_success",
        "strategy_return_percent",
        "buy_and_hold_return_percent",
        "excess_return_percent",
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
        "return_score",
        "sharpe_score",
        "drawdown_score",
        "profit_factor_score",
        "walk_forward_component_score",
        "trade_quality_score",
        "final_score",
        "final_status",
        "passed_minimum_trades",
        "passed_drawdown_limit",
        "passed_profit_factor",
        "passed_sharpe",
        "passed_walk_forward",
        "passed_all_checks",
        "error_message",
        "reasons",
        "warnings",
    }

    for candidate in report.candidates:
        candidate_name = str(
            candidate.get(
                "candidate_name",
                "UNKNOWN",
            )
        )

        missing_keys = (
            required_keys
            - set(candidate.keys())
        )

        if missing_keys:
            raise RuntimeError(
                f"{candidate_name}에 필수 키가 없습니다: "
                f"{sorted(missing_keys)}"
            )

        candidate_type = str(
            candidate["candidate_type"]
        )

        if candidate_type not in VALID_CANDIDATE_TYPES:
            raise RuntimeError(
                f"{candidate_name}의 Candidate Type이 "
                f"올바르지 않습니다: {candidate_type}"
            )

        final_status = str(
            candidate["final_status"]
        )

        if final_status not in VALID_FINAL_STATUSES:
            raise RuntimeError(
                f"{candidate_name}의 Final Status가 "
                f"올바르지 않습니다: {final_status}"
            )

        walk_forward_status = str(
            candidate["walk_forward_status"]
        )

        if (
            walk_forward_status
            not in VALID_WALK_FORWARD_STATUSES
        ):
            raise RuntimeError(
                f"{candidate_name}의 Walk-Forward Status가 "
                f"올바르지 않습니다: "
                f"{walk_forward_status}"
            )

        score_fields = (
            "generator_priority_score",
            "walk_forward_score",
            "parameter_stability_score",
            "return_score",
            "sharpe_score",
            "drawdown_score",
            "profit_factor_score",
            "walk_forward_component_score",
            "trade_quality_score",
            "final_score",
        )

        for field in score_fields:
            value = float(
                candidate[field]
            )

            if not 0.0 <= value <= 100.0:
                raise RuntimeError(
                    f"{candidate_name}의 {field} 값이 "
                    f"0~100 범위를 벗어났습니다: "
                    f"{value:.2f}"
                )

        percentage_fields = (
            "win_rate_percent",
            "profitable_windows_percent",
            "acceptable_windows_percent",
            "beat_default_return_percent",
        )

        for field in percentage_fields:
            value = float(
                candidate[field]
            )

            if not 0.0 <= value <= 100.0:
                raise RuntimeError(
                    f"{candidate_name}의 {field} 값이 "
                    f"0~100 범위를 벗어났습니다: "
                    f"{value:.2f}"
                )

        if int(candidate["total_trades"]) < 0:
            raise RuntimeError(
                f"{candidate_name}의 거래 횟수가 "
                "음수입니다."
            )

        if int(candidate["maximum_holding_days"]) <= 0:
            raise RuntimeError(
                f"{candidate_name}의 최대 보유기간이 "
                "0 이하입니다."
            )

        if float(candidate["position_percent"]) <= 0:
            raise RuntimeError(
                f"{candidate_name}의 포지션 비율이 "
                "0 이하입니다."
            )

        if not isinstance(
            candidate["reasons"],
            list,
        ):
            raise RuntimeError(
                f"{candidate_name}의 reasons가 "
                "목록이 아닙니다."
            )

        if not isinstance(
            candidate["warnings"],
            list,
        ):
            raise RuntimeError(
                f"{candidate_name}의 warnings가 "
                "목록이 아닙니다."
            )

        expected_passed_all = all(
            [
                bool(candidate["backtest_success"]),
                bool(candidate["walk_forward_success"]),
                bool(candidate["passed_minimum_trades"]),
                bool(candidate["passed_drawdown_limit"]),
                bool(candidate["passed_profit_factor"]),
                bool(candidate["passed_sharpe"]),
                bool(candidate["passed_walk_forward"]),
            ]
        )

        if (
            expected_passed_all
            != bool(candidate["passed_all_checks"])
        ):
            raise RuntimeError(
                f"{candidate_name}의 Passed All Checks "
                "계산이 일치하지 않습니다."
            )

        if (
            bool(candidate["passed_all_checks"])
            and final_status
            not in {
                "ROBUST",
                "ACCEPTABLE",
                "WEAK",
            }
        ):
            raise RuntimeError(
                f"{candidate_name}은 모든 검사를 "
                "통과했지만 Final Status가 "
                f"{final_status}입니다."
            )


def validate_report_structure(
    report: ImprovementCandidateBacktestReport,
) -> None:
    """
    V8.3 전체 집계와 우승 후보 정보를 검사합니다.
    """

    if report.version != "V8.3":
        raise RuntimeError(
            f"보고서 버전이 V8.3이 아닙니다: "
            f"{report.version}"
        )

    if report.tested_candidates <= 0:
        raise RuntimeError(
            "테스트된 후보가 없습니다."
        )

    if (
        len(report.candidates)
        != report.tested_candidates
    ):
        raise RuntimeError(
            "후보 목록 길이와 Tested Candidates가 "
            "일치하지 않습니다."
        )

    if (
        report.successful_candidates
        + report.failed_candidates
        != report.tested_candidates
    ):
        raise RuntimeError(
            "Successful Candidates와 Failed Candidates의 "
            "합계가 Tested Candidates와 다릅니다."
        )

    if (
        report.passed_candidates
        + report.rejected_candidates
        != report.tested_candidates
    ):
        raise RuntimeError(
            "Passed Candidates와 Rejected Candidates의 "
            "합계가 Tested Candidates와 다릅니다."
        )

    calculated_successful = sum(
        1
        for candidate in report.candidates
        if (
            bool(candidate["backtest_success"])
            and bool(
                candidate[
                    "walk_forward_success"
                ]
            )
        )
    )

    if (
        calculated_successful
        != report.successful_candidates
    ):
        raise RuntimeError(
            "Successful Candidates 집계가 "
            "일치하지 않습니다."
        )

    calculated_passed = sum(
        1
        for candidate in report.candidates
        if bool(
            candidate["passed_all_checks"]
        )
    )

    if calculated_passed != report.passed_candidates:
        raise RuntimeError(
            "Passed Candidates 집계가 "
            "일치하지 않습니다."
        )

    expected_ranks = list(
        range(
            1,
            report.tested_candidates + 1,
        )
    )

    actual_ranks = [
        int(candidate["rank"])
        for candidate in report.candidates
    ]

    if actual_ranks != expected_ranks:
        raise RuntimeError(
            "후보 순위가 1부터 연속적으로 "
            "정렬되지 않았습니다."
        )

    if not check_candidate_ranking(report):
        raise RuntimeError(
            "후보들이 통과 여부와 최종 점수를 기준으로 "
            "올바르게 정렬되지 않았습니다."
        )

    winner = find_winner(
        report
    )

    if winner is None:
        raise RuntimeError(
            "최종 우승 후보를 찾을 수 없습니다."
        )

    if int(winner["rank"]) != 1:
        raise RuntimeError(
            "최종 우승 후보가 1위가 아닙니다."
        )

    if abs(
        float(winner["final_score"])
        - report.winner_final_score
    ) > 0.01:
        raise RuntimeError(
            "Winner Final Score가 1위 후보 점수와 "
            "일치하지 않습니다."
        )

    if (
        str(winner["candidate_type"])
        != report.winner_candidate_type
    ):
        raise RuntimeError(
            "Winner Candidate Type이 1위 후보와 "
            "일치하지 않습니다."
        )

    if (
        str(winner["final_status"])
        != report.winner_status
    ):
        raise RuntimeError(
            "Winner Status가 1위 후보와 "
            "일치하지 않습니다."
        )

    expected_improvement = round(
        report.winner_final_score
        - report.baseline_final_score,
        2,
    )

    if abs(
        expected_improvement
        - report.improvement_over_baseline_score
    ) > 0.01:
        raise RuntimeError(
            "Improvement Over Baseline Score 계산이 "
            "일치하지 않습니다."
        )

    winner_parameter_checks = {
        "Entry score": (
            report.winner_entry_score,
            float(winner["entry_score"]),
        ),
        "Exit score": (
            report.winner_exit_score,
            float(winner["exit_score"]),
        ),
        "Stop ATR": (
            report.winner_stop_atr,
            float(
                winner["stop_atr_multiple"]
            ),
        ),
        "Target ATR": (
            report.winner_target_atr,
            float(
                winner["target_atr_multiple"]
            ),
        ),
        "Position percent": (
            report.winner_position_percent,
            float(
                winner["position_percent"]
            ),
        ),
    }

    for name, values in winner_parameter_checks.items():
        report_value, candidate_value = values

        if report_value is None:
            raise RuntimeError(
                f"Winner {name} 값이 없습니다."
            )

        if abs(
            float(report_value)
            - candidate_value
        ) > 0.01:
            raise RuntimeError(
                f"Winner {name} 값이 1위 후보와 "
                "일치하지 않습니다."
            )

    if report.winner_holding_days is None:
        raise RuntimeError(
            "Winner Holding Days 값이 없습니다."
        )

    if (
        int(report.winner_holding_days)
        != int(
            winner["maximum_holding_days"]
        )
    ):
        raise RuntimeError(
            "Winner Holding Days가 1위 후보와 "
            "일치하지 않습니다."
        )

    validate_candidate_structure(
        report
    )


def validate_saved_files(
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.3 JSON 보고서 저장 여부를 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            "시간별 Improvement Candidate Backtest "
            f"보고서가 없습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            "Latest Improvement Candidate Backtest "
            f"보고서가 없습니다: {latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 Improvement Candidate Backtest "
            "보고서가 비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "Latest Improvement Candidate Backtest "
            "보고서가 비어 있습니다."
        )


def main() -> None:
    """
    V8.3 Improvement Candidate Backtester
    통합 테스트입니다.

    V8.2에서 생성된 상위 후보들을 전체 백테스트와
    Walk-Forward 방식으로 실제 검증하고,
    후보별 점수와 품질 검사 및 최종 우승 후보를
    자동으로 확인합니다.
    """

    symbol = "AAPL"

    # 처음에는 실행 시간을 줄이기 위해
    # 상위 5개 후보만 테스트합니다.
    #
    # 정상 동작 확인 후 10 또는 15로
    # 늘릴 수 있습니다.
    maximum_candidates = 5

    print_test_header()

    try:
        report = run_improvement_candidate_backtest(
            symbol=symbol,

            maximum_candidates=(
                maximum_candidates
            ),

            period="10y",
            interval="1d",

            initial_cash=10000.0,

            # 현재 테스트에서는 기존 백테스트와
            # 동일하게 거래당 수수료를 $0으로 둡니다.
            commission_per_trade=0.0,

            training_years=4.0,
            validation_years=1.0,
            step_years=1.0,

            estimated_trading_days_per_year=252,

            minimum_trades=30,
            maximum_drawdown_limit=15.0,
        )

        (
            report_path,
            latest_path,
        ) = save_improvement_candidate_backtest(
            report
        )

        # 저장 후 파일 경로가 포함된 상태로
        # 최종 결과를 다시 출력합니다.
        print_improvement_candidate_backtest(
            report
        )

        print_candidate_details(
            report
        )

        print_test_summary(
            report=report,
            report_path=report_path,
            latest_path=latest_path,
        )

        validate_report_structure(
            report
        )

        validate_saved_files(
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V8.3 improvement candidate "
            "backtester test completed successfully."
        )

        print(
            "V8.2에서 생성된 상위 개선 후보를 "
            "전체 백테스트와 Walk-Forward 방식으로 "
            "정상적으로 비교했습니다."
        )

        print(
            "주의: 이 결과는 과거 데이터 기반 연구용 "
            "시뮬레이션이며 실제 투자 조언, 주문 지시 "
            "또는 미래 수익 보장이 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 160)
        print("TEST CANCELLED")
        print("=" * 160)

        print(
            "사용자가 V8.3 Improvement Candidate "
            "Backtester 테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 160)
        print(
            "V8.3 IMPROVEMENT CANDIDATE "
            "BACKTESTER ERROR"
        )
        print("=" * 160)

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