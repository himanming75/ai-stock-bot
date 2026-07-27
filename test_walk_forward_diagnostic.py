from pathlib import Path
from typing import Any

from backtest.walk_forward_diagnostic import (
    WalkForwardDiagnosticResult,
    print_walk_forward_diagnostic,
    run_walk_forward_diagnostic,
    save_walk_forward_diagnostic,
)


def print_test_header() -> None:
    """
    V8.1 Walk-Forward Diagnostic 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 150)
    print(
        "AI STOCK BOT V8.1 "
        "WALK-FORWARD DIAGNOSTIC TEST"
    )
    print("=" * 150)


def format_value(
    value: Any,
) -> str:
    """
    여러 형태의 값을 출력하기 좋은 문자열로 변환합니다.
    """

    if value is None:
        return "N/A"

    if isinstance(
        value,
        bool,
    ):
        return str(
            value
        )

    if isinstance(
        value,
        float,
    ):
        return f"{value:.2f}"

    return str(
        value
    )


def print_window_diagnostics(
    result: WalkForwardDiagnosticResult,
) -> None:
    """
    각 Walk-Forward 검증 구간의 상세 진단을 출력합니다.
    """

    print()
    print("=" * 150)
    print("WINDOW DIAGNOSTIC DETAILS")
    print("=" * 150)

    for window in result.windows:
        window_number = int(
            window[
                "window_number"
            ]
        )

        print()
        print("-" * 150)

        print(
            f"WINDOW {window_number}/"
            f"{result.successful_windows}"
        )

        print("-" * 150)

        print(
            f"Training period              : "
            f"{window['training_start']} "
            f"to {window['training_end']}"
        )

        print(
            f"Validation period            : "
            f"{window['validation_start']} "
            f"to {window['validation_end']}"
        )

        print()
        print("SELECTED PARAMETERS")
        print("-" * 150)

        print(
            f"Entry score                  : "
            f"{float(window['entry_score']):.2f}"
        )

        print(
            f"Exit score                   : "
            f"{float(window['exit_score']):.2f}"
        )

        print(
            f"Stop ATR                     : "
            f"{float(window['stop_atr_multiple']):.2f}"
        )

        print(
            f"Target ATR                   : "
            f"{float(window['target_atr_multiple']):.2f}"
        )

        print(
            f"Maximum holding days         : "
            f"{int(window['maximum_holding_days'])}"
        )

        print(
            f"Position percent             : "
            f"{float(window['position_percent']):.2f}%"
        )

        print()
        print("VALIDATION PERFORMANCE")
        print("-" * 150)

        print(
            f"Strategy return              : "
            f"{float(window['strategy_return_percent']):.2f}%"
        )

        print(
            f"Default return               : "
            f"{float(window['default_return_percent']):.2f}%"
        )

        print(
            f"Excess return                : "
            f"{float(window['excess_return_percent']):.2f}%p"
        )

        print(
            f"Sharpe ratio                 : "
            f"{float(window['sharpe_ratio']):.2f}"
        )

        print(
            f"Default Sharpe               : "
            f"{float(window['default_sharpe_ratio']):.2f}"
        )

        print(
            f"Maximum drawdown             : "
            f"{float(window['maximum_drawdown_percent']):.2f}%"
        )

        print(
            f"Profit factor                : "
            f"{float(window['profit_factor']):.2f}"
        )

        print(
            f"Win rate                     : "
            f"{float(window['win_rate_percent']):.2f}%"
        )

        print(
            f"Total trades                 : "
            f"{int(window['total_trades'])}"
        )

        print()
        print("PERFORMANCE RETENTION")
        print("-" * 150)

        print(
            f"Return retention             : "
            f"{float(window['return_retention_percent']):.2f}%"
        )

        print(
            f"Sharpe retention             : "
            f"{float(window['sharpe_retention_percent']):.2f}%"
        )

        print()
        print("DIAGNOSTIC SCORES")
        print("-" * 150)

        print(
            f"Return score                 : "
            f"{float(window['return_score']):.2f}/100"
        )

        print(
            f"Sharpe score                 : "
            f"{float(window['sharpe_score']):.2f}/100"
        )

        print(
            f"Drawdown score               : "
            f"{float(window['drawdown_score']):.2f}/100"
        )

        print(
            f"Profit factor score          : "
            f"{float(window['profit_factor_score']):.2f}/100"
        )

        print(
            f"Consistency score            : "
            f"{float(window['consistency_score']):.2f}/100"
        )

        print(
            f"Diagnostic score             : "
            f"{float(window['diagnostic_score']):.2f}/100"
        )

        print(
            f"Diagnostic status            : "
            f"{window['diagnostic_status']}"
        )

        print()
        print("VALIDATION FLAGS")
        print("-" * 150)

        print(
            f"Profitable                    : "
            f"{window['profitable']}"
        )

        print(
            f"Beat default return           : "
            f"{window['beat_default_return']}"
        )

        print(
            f"Beat default Sharpe           : "
            f"{window['beat_default_sharpe']}"
        )

        print(
            f"Acceptable                    : "
            f"{window['acceptable']}"
        )

        problems = window.get(
            "problems",
            [],
        )

        if problems:
            print()
            print("PROBLEMS")
            print("-" * 150)

            for problem in problems:
                print(
                    f"- {problem}"
                )

        strengths = window.get(
            "strengths",
            [],
        )

        if strengths:
            print()
            print("STRENGTHS")
            print("-" * 150)

            for strength in strengths:
                print(
                    f"- {strength}"
                )


def print_test_summary(
    result: WalkForwardDiagnosticResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.1 테스트 결과를 요약하여 출력합니다.
    """

    print()
    print("=" * 150)
    print(
        "V8.1 WALK-FORWARD "
        "DIAGNOSTIC TEST RESULT"
    )
    print("=" * 150)

    print(
        f"Symbol                        : "
        f"{result.symbol}"
    )

    print(
        f"Validation status             : "
        f"{result.validation_status}"
    )

    print(
        f"Overall diagnostic score      : "
        f"{result.overall_diagnostic_score:.2f}/100"
    )

    print(
        f"Overfitting warning           : "
        f"{result.overfitting_warning}"
    )

    print(
        f"Recent performance trend      : "
        f"{result.recent_trend}"
    )

    print(
        f"Elapsed time                  : "
        f"{result.elapsed_seconds:.2f} seconds"
    )

    print()
    print("WINDOW SUMMARY")
    print("-" * 150)

    print(
        f"Total windows                 : "
        f"{result.total_windows}"
    )

    print(
        f"Successful windows            : "
        f"{result.successful_windows}"
    )

    print(
        f"Failed windows                : "
        f"{result.failed_windows}"
    )

    print(
        f"Profitable windows            : "
        f"{result.profitable_windows}/"
        f"{result.successful_windows} "
        f"({result.profitable_percent:.2f}%)"
    )

    print(
        f"Acceptable windows            : "
        f"{result.acceptable_windows}/"
        f"{result.successful_windows} "
        f"({result.acceptable_percent:.2f}%)"
    )

    print(
        f"Beat default return           : "
        f"{result.beat_default_return_windows}/"
        f"{result.successful_windows} "
        f"({result.beat_default_return_percent:.2f}%)"
    )

    print(
        f"Beat default Sharpe           : "
        f"{result.beat_default_sharpe_windows}/"
        f"{result.successful_windows} "
        f"({result.beat_default_sharpe_percent:.2f}%)"
    )

    print()
    print("PERFORMANCE SUMMARY")
    print("-" * 150)

    print(
        f"Average strategy return       : "
        f"{result.average_strategy_return_percent:.2f}%"
    )

    print(
        f"Median strategy return        : "
        f"{result.median_strategy_return_percent:.2f}%"
    )

    print(
        f"Best strategy return          : "
        f"{result.best_strategy_return_percent:.2f}%"
    )

    print(
        f"Worst strategy return         : "
        f"{result.worst_strategy_return_percent:.2f}%"
    )

    print(
        f"Average default return        : "
        f"{result.average_default_return_percent:.2f}%"
    )

    print(
        f"Average excess return         : "
        f"{result.average_excess_return_percent:.2f}%p"
    )

    print(
        f"Average Sharpe                : "
        f"{result.average_sharpe_ratio:.2f}"
    )

    print(
        f"Median Sharpe                 : "
        f"{result.median_sharpe_ratio:.2f}"
    )

    print(
        f"Worst drawdown                : "
        f"{result.worst_drawdown_percent:.2f}%"
    )

    print(
        f"Average profit factor         : "
        f"{result.average_profit_factor:.2f}"
    )

    print(
        f"Total validation trades       : "
        f"{result.total_validation_trades}"
    )

    print()
    print("CONSISTENCY SUMMARY")
    print("-" * 150)

    print(
        f"Parameter stability score     : "
        f"{result.parameter_stability_score:.2f}/100"
    )

    print(
        f"Performance consistency score : "
        f"{result.performance_consistency_score:.2f}/100"
    )

    print(
        f"Recent performance score      : "
        f"{result.recent_performance_score:.2f}/100"
    )

    print(
        f"Average return retention      : "
        f"{result.average_return_retention_percent:.2f}%"
    )

    print(
        f"Average Sharpe retention      : "
        f"{result.average_sharpe_retention_percent:.2f}%"
    )

    print()
    print("BEST AND WORST WINDOWS")
    print("-" * 150)

    print(
        f"Best window number            : "
        f"{result.best_window_number}"
    )

    print(
        f"Worst window number           : "
        f"{result.worst_window_number}"
    )

    print()
    print("COMMON PARAMETERS")
    print("-" * 150)

    print(
        f"Most common entry score       : "
        f"{format_value(result.most_common_entry_score)}"
    )

    print(
        f"Most common exit score        : "
        f"{format_value(result.most_common_exit_score)}"
    )

    print(
        f"Most common stop ATR          : "
        f"{format_value(result.most_common_stop_atr)}"
    )

    print(
        f"Most common target ATR        : "
        f"{format_value(result.most_common_target_atr)}"
    )

    print(
        f"Most common holding days      : "
        f"{format_value(result.most_common_holding_days)}"
    )

    print()
    print("VALIDATION CHECKS")
    print("-" * 150)

    all_windows_processed = (
        (
            result.successful_windows
            + result.failed_windows
        )
        == result.total_windows
    )

    no_failed_windows = (
        result.failed_windows == 0
    )

    window_count_matches = (
        len(
            result.windows
        )
        == result.successful_windows
    )

    overall_score_is_valid = (
        0.0
        <= result.overall_diagnostic_score
        <= 100.0
    )

    parameter_score_is_valid = (
        0.0
        <= result.parameter_stability_score
        <= 100.0
    )

    consistency_score_is_valid = (
        0.0
        <= result.performance_consistency_score
        <= 100.0
    )

    recent_score_is_valid = (
        0.0
        <= result.recent_performance_score
        <= 100.0
    )

    print(
        f"All windows processed         : "
        f"{all_windows_processed}"
    )

    print(
        f"No failed windows             : "
        f"{no_failed_windows}"
    )

    print(
        f"Window count matches          : "
        f"{window_count_matches}"
    )

    print(
        f"Overall score is valid        : "
        f"{overall_score_is_valid}"
    )

    print(
        f"Parameter score is valid      : "
        f"{parameter_score_is_valid}"
    )

    print(
        f"Consistency score is valid    : "
        f"{consistency_score_is_valid}"
    )

    print(
        f"Recent score is valid         : "
        f"{recent_score_is_valid}"
    )

    print()
    print("FILES")
    print("-" * 150)

    print(
        f"Source file                   : "
        f"{result.source_file}"
    )

    print(
        f"Report file                   : "
        f"{report_path}"
    )

    print(
        f"Latest file                   : "
        f"{latest_path}"
    )

    print("=" * 150)


def validate_window_structure(
    result: WalkForwardDiagnosticResult,
) -> None:
    """
    각 Walk-Forward Window 결과 구조를 검사합니다.
    """

    required_keys = {
        "window_number",
        "training_start",
        "training_end",
        "validation_start",
        "validation_end",
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
        "strategy_return_percent",
        "default_return_percent",
        "excess_return_percent",
        "sharpe_ratio",
        "default_sharpe_ratio",
        "maximum_drawdown_percent",
        "profit_factor",
        "win_rate_percent",
        "total_trades",
        "return_retention_percent",
        "sharpe_retention_percent",
        "return_score",
        "sharpe_score",
        "drawdown_score",
        "profit_factor_score",
        "consistency_score",
        "diagnostic_score",
        "diagnostic_status",
        "profitable",
        "beat_default_return",
        "beat_default_sharpe",
        "acceptable",
        "problems",
        "strengths",
    }

    valid_statuses = {
        "ROBUST",
        "ACCEPTABLE",
        "WEAK",
        "FAILED",
    }

    for window in result.windows:
        missing_keys = (
            required_keys
            - set(
                window.keys()
            )
        )

        if missing_keys:
            raise RuntimeError(
                f"Window {window.get('window_number')}에 "
                "필수 키가 없습니다: "
                f"{sorted(missing_keys)}"
            )

        diagnostic_score = float(
            window[
                "diagnostic_score"
            ]
        )

        if not (
            0.0
            <= diagnostic_score
            <= 100.0
        ):
            raise RuntimeError(
                f"Window {window['window_number']}의 "
                "Diagnostic Score가 0~100 범위를 "
                "벗어났습니다."
            )

        score_fields = [
            "return_score",
            "sharpe_score",
            "drawdown_score",
            "profit_factor_score",
            "consistency_score",
        ]

        for score_field in score_fields:
            score_value = float(
                window[
                    score_field
                ]
            )

            if not (
                0.0
                <= score_value
                <= 100.0
            ):
                raise RuntimeError(
                    f"Window {window['window_number']}의 "
                    f"{score_field} 값이 0~100 범위를 "
                    "벗어났습니다."
                )

        status = str(
            window[
                "diagnostic_status"
            ]
        )

        if status not in valid_statuses:
            raise RuntimeError(
                f"Window {window['window_number']}의 "
                f"상태가 올바르지 않습니다: {status}"
            )

        total_trades = int(
            window[
                "total_trades"
            ]
        )

        if total_trades < 0:
            raise RuntimeError(
                f"Window {window['window_number']}의 "
                "거래 횟수가 음수입니다."
            )


def validate_result_structure(
    result: WalkForwardDiagnosticResult,
) -> None:
    """
    V8.1 전체 결과 구조와 집계값을 검사합니다.
    """

    if result.total_windows <= 0:
        raise RuntimeError(
            "Walk-Forward 전체 구간 수가 0입니다."
        )

    if (
        result.successful_windows
        + result.failed_windows
        != result.total_windows
    ):
        raise RuntimeError(
            "Successful Windows와 Failed Windows의 "
            "합계가 Total Windows와 다릅니다."
        )

    if (
        len(
            result.windows
        )
        != result.successful_windows
    ):
        raise RuntimeError(
            "windows 목록 길이와 Successful Windows가 "
            "일치하지 않습니다."
        )

    score_fields = {
        "overall_diagnostic_score": (
            result.overall_diagnostic_score
        ),

        "parameter_stability_score": (
            result.parameter_stability_score
        ),

        "performance_consistency_score": (
            result.performance_consistency_score
        ),

        "recent_performance_score": (
            result.recent_performance_score
        ),
    }

    for score_name, score_value in score_fields.items():
        if not (
            0.0
            <= score_value
            <= 100.0
        ):
            raise RuntimeError(
                f"{score_name} 값이 0~100 범위를 "
                f"벗어났습니다: {score_value:.2f}"
            )

    expected_profitable_windows = sum(
        1
        for window in result.windows
        if bool(
            window[
                "profitable"
            ]
        )
    )

    if (
        expected_profitable_windows
        != result.profitable_windows
    ):
        raise RuntimeError(
            "Window 목록에서 계산한 Profitable Windows와 "
            "집계값이 일치하지 않습니다."
        )

    expected_acceptable_windows = sum(
        1
        for window in result.windows
        if bool(
            window[
                "acceptable"
            ]
        )
    )

    if (
        expected_acceptable_windows
        != result.acceptable_windows
    ):
        raise RuntimeError(
            "Window 목록에서 계산한 Acceptable Windows와 "
            "집계값이 일치하지 않습니다."
        )

    expected_beat_default_return = sum(
        1
        for window in result.windows
        if bool(
            window[
                "beat_default_return"
            ]
        )
    )

    if (
        expected_beat_default_return
        != result.beat_default_return_windows
    ):
        raise RuntimeError(
            "기본 전략 수익률 초과 구간 집계값이 "
            "일치하지 않습니다."
        )

    expected_beat_default_sharpe = sum(
        1
        for window in result.windows
        if bool(
            window[
                "beat_default_sharpe"
            ]
        )
    )

    if (
        expected_beat_default_sharpe
        != result.beat_default_sharpe_windows
    ):
        raise RuntimeError(
            "기본 Sharpe 초과 구간 집계값이 "
            "일치하지 않습니다."
        )

    if result.successful_windows > 0:
        expected_profitable_percent = round(
            (
                result.profitable_windows
                / result.successful_windows
                * 100.0
            ),
            2,
        )

        if abs(
            expected_profitable_percent
            - result.profitable_percent
        ) > 0.01:
            raise RuntimeError(
                "Profitable Percent 계산값이 "
                "일치하지 않습니다."
            )

        expected_acceptable_percent = round(
            (
                result.acceptable_windows
                / result.successful_windows
                * 100.0
            ),
            2,
        )

        if abs(
            expected_acceptable_percent
            - result.acceptable_percent
        ) > 0.01:
            raise RuntimeError(
                "Acceptable Percent 계산값이 "
                "일치하지 않습니다."
            )

    if result.best_window_number is None:
        raise RuntimeError(
            "Best Window Number가 없습니다."
        )

    if result.worst_window_number is None:
        raise RuntimeError(
            "Worst Window Number가 없습니다."
        )

    valid_window_numbers = {
        int(
            window[
                "window_number"
            ]
        )
        for window in result.windows
    }

    if (
        result.best_window_number
        not in valid_window_numbers
    ):
        raise RuntimeError(
            "Best Window Number가 실제 Window 목록에 "
            "존재하지 않습니다."
        )

    if (
        result.worst_window_number
        not in valid_window_numbers
    ):
        raise RuntimeError(
            "Worst Window Number가 실제 Window 목록에 "
            "존재하지 않습니다."
        )

    valid_statuses = {
        "ROBUST",
        "ACCEPTABLE",
        "WEAK",
        "FAILED",
    }

    if (
        result.validation_status
        not in valid_statuses
    ):
        raise RuntimeError(
            "전체 Validation Status가 올바르지 않습니다: "
            f"{result.validation_status}"
        )

    valid_trends = {
        "IMPROVING",
        "STABLE",
        "DETERIORATING",
        "UNKNOWN",
    }

    if (
        result.recent_trend
        not in valid_trends
    ):
        raise RuntimeError(
            "Recent Performance Trend 값이 "
            f"올바르지 않습니다: {result.recent_trend}"
        )

    validate_window_structure(
        result
    )


def validate_saved_files(
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V8.1 JSON 보고서 저장 여부를 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            "시간별 Walk-Forward Diagnostic "
            f"보고서가 생성되지 않았습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            "Latest Walk-Forward Diagnostic "
            f"보고서가 생성되지 않았습니다: {latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 Walk-Forward Diagnostic "
            "보고서가 비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "Latest Walk-Forward Diagnostic "
            "보고서가 비어 있습니다."
        )


def main() -> None:
    """
    V8.1 Walk-Forward Diagnostic 통합 테스트입니다.

    V7.4 Walk-Forward latest JSON 파일을 읽고
    각 검증 구간의 수익률, Sharpe, 낙폭, Profit Factor,
    파라미터 안정성 및 최근 성과 추세를 진단합니다.
    """

    symbol = "AAPL"

    print_test_header()

    try:
        result = run_walk_forward_diagnostic(
            symbol=symbol
        )

        (
            report_path,
            latest_path,
        ) = save_walk_forward_diagnostic(
            result
        )

        print_walk_forward_diagnostic(
            result
        )

        print_window_diagnostics(
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
            "V8.1 walk-forward diagnostic test "
            "completed successfully."
        )

        print(
            "V7.4 Walk-Forward 결과의 각 검증 구간과 "
            "낮은 종합 점수의 원인을 분석했습니다."
        )

        print(
            "주의: 이 결과는 과거 데이터 기반 연구용 "
            "진단이며 실제 투자 조언이나 미래 수익 "
            "보장이 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 150)
        print("TEST CANCELLED")
        print("=" * 150)

        print(
            "사용자가 V8.1 Walk-Forward Diagnostic "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 150)
        print(
            "V8.1 WALK-FORWARD DIAGNOSTIC ERROR"
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