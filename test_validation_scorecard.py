from pathlib import Path
from typing import Any

from backtest.validation_scorecard import (
    StrategyValidationScorecard,
    print_strategy_validation_scorecard,
    run_strategy_validation_scorecard,
    save_strategy_validation_scorecard,
)


def print_test_header() -> None:
    """
    V8.0 종합 전략 검증 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V8.0 "
        "STRATEGY VALIDATION SCORECARD TEST"
    )
    print("=" * 140)


def format_metric_value(
    value: Any,
) -> str:
    """
    검증 항목의 값을 보기 좋은 문자열로 변환합니다.
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


def print_component_details(
    result: StrategyValidationScorecard,
) -> None:
    """
    각 검증 항목의 핵심 지표와 원본 파일을 출력합니다.
    """

    print()
    print("=" * 140)
    print("COMPONENT DETAILS")
    print("=" * 140)

    for number, component in enumerate(
        result.components,
        start=1,
    ):
        print()
        print("-" * 140)

        print(
            f"[{number}/{result.total_components}] "
            f"{component['version']} "
            f"{component['component_name']}"
        )

        print("-" * 140)

        print(
            f"Component key       : "
            f"{component['component_key']}"
        )

        print(
            f"Status              : "
            f"{component['status']}"
        )

        print(
            f"Passed              : "
            f"{component['passed']}"
        )

        print(
            f"Warning             : "
            f"{component['warning']}"
        )

        print(
            f"Weight              : "
            f"{float(component['weight']):.2f}%"
        )

        print(
            f"Raw score           : "
            f"{float(component['raw_score']):.2f}/100"
        )

        print(
            f"Weighted score      : "
            f"{float(component['weighted_score']):.2f}"
        )

        print(
            f"Source file         : "
            f"{component['source_file'] or 'Not found'}"
        )

        metrics = component.get(
            "metrics",
            {},
        )

        if metrics:
            print()
            print("Metrics")
            print("-" * 140)

            for metric_name, metric_value in metrics.items():
                print(
                    f"{metric_name:<42}: "
                    f"{format_metric_value(metric_value)}"
                )

        reasons = component.get(
            "reasons",
            [],
        )

        if reasons:
            print()
            print("Reasons")
            print("-" * 140)

            for reason in reasons:
                print(
                    f"- {reason}"
                )

        warnings = component.get(
            "warnings",
            [],
        )

        if warnings:
            print()
            print("Warnings")
            print("-" * 140)

            for warning in warnings:
                print(
                    f"- {warning}"
                )

        error_type = component.get(
            "error_type"
        )

        error_message = component.get(
            "error_message"
        )

        if (
            error_type
            or error_message
        ):
            print()
            print("Error")
            print("-" * 140)

            print(
                f"Error type          : "
                f"{error_type or 'N/A'}"
            )

            print(
                f"Error message       : "
                f"{error_message or 'N/A'}"
            )


def print_test_summary(
    result: StrategyValidationScorecard,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    테스트 완료 후 종합 결과를 다시 요약합니다.
    """

    print()
    print("=" * 140)
    print(
        "V8.0 STRATEGY VALIDATION "
        "SCORECARD TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                       : "
        f"{result.symbol}"
    )

    print(
        f"Final score                  : "
        f"{result.final_score:.2f}/100"
    )

    print(
        f"Validation status            : "
        f"{result.validation_status}"
    )

    print(
        f"Deployment readiness         : "
        f"{result.deployment_readiness}"
    )

    print(
        f"Critical failure             : "
        f"{result.critical_failure}"
    )

    print(
        f"Overfitting warning          : "
        f"{result.overfitting_warning}"
    )

    print(
        f"Elapsed time                 : "
        f"{result.elapsed_seconds:.2f} seconds"
    )

    print()
    print("COMPONENT COUNTS")
    print("-" * 140)

    print(
        f"Total components             : "
        f"{result.total_components}"
    )

    print(
        f"Loaded components            : "
        f"{result.loaded_components}"
    )

    print(
        f"Missing components           : "
        f"{result.missing_components}"
    )

    print(
        f"Failed components            : "
        f"{result.failed_components}"
    )

    print(
        f"Passed components            : "
        f"{result.passed_components}"
    )

    print(
        f"Warning components           : "
        f"{result.warning_components}"
    )

    print()
    print("WEIGHTED SCORE")
    print("-" * 140)

    print(
        f"Total weight                 : "
        f"{result.total_weight:.2f}"
    )

    print(
        f"Earned weighted score        : "
        f"{result.earned_weighted_score:.2f}"
    )

    print(
        f"Final normalized score       : "
        f"{result.final_score:.2f}/100"
    )

    print()
    print("COMPONENT RANKING")
    print("-" * 140)

    ranked_components = sorted(
        result.components,
        key=lambda component: float(
            component["raw_score"]
        ),
        reverse=True,
    )

    print(
        f"{'Rank':<7}"
        f"{'Version':<10}"
        f"{'Validation':<34}"
        f"{'Score':>12}"
        f"{'Weight':>12}"
        f"{'Weighted':>14}"
        f"{'Passed':>10}"
        f"{'Warning':>10}"
        f"{'Status':>18}"
    )

    print("-" * 140)

    for rank, component in enumerate(
        ranked_components,
        start=1,
    ):
        print(
            f"{rank:<7}"
            f"{component['version']:<10}"
            f"{component['component_name']:<34}"
            f"{float(component['raw_score']):>11.2f}"
            f"{float(component['weight']):>11.2f}%"
            f"{float(component['weighted_score']):>14.2f}"
            f"{str(component['passed']):>10}"
            f"{str(component['warning']):>10}"
            f"{str(component['status']):>18}"
        )

    print()
    print("VALIDATION CHECKS")
    print("-" * 140)

    all_components_loaded = (
        result.loaded_components
        == result.total_components
    )

    no_missing_components = (
        result.missing_components == 0
    )

    no_failed_components = (
        result.failed_components == 0
    )

    total_weight_is_100 = (
        abs(
            result.total_weight
            - 100.0
        )
        < 0.001
    )

    score_is_valid = (
        0.0
        <= result.final_score
        <= 100.0
    )

    component_count_is_valid = (
        (
            result.loaded_components
            + result.missing_components
            + result.failed_components
        )
        == result.total_components
    )

    print(
        f"All components loaded        : "
        f"{all_components_loaded}"
    )

    print(
        f"No missing components        : "
        f"{no_missing_components}"
    )

    print(
        f"No failed components         : "
        f"{no_failed_components}"
    )

    print(
        f"Total weight equals 100      : "
        f"{total_weight_is_100}"
    )

    print(
        f"Final score is 0 to 100      : "
        f"{score_is_valid}"
    )

    print(
        f"Component count is valid     : "
        f"{component_count_is_valid}"
    )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Report file                  : "
        f"{report_path}"
    )

    print(
        f"Latest file                  : "
        f"{latest_path}"
    )

    print("=" * 140)


def validate_scorecard_structure(
    result: StrategyValidationScorecard,
) -> None:
    """
    V8.0 결과 구조와 계산값을 자동 검사합니다.
    """

    if result.total_components <= 0:
        raise RuntimeError(
            "전체 검증 항목 수가 0입니다."
        )

    if len(
        result.components
    ) != result.total_components:
        raise RuntimeError(
            "components 목록 길이가 "
            "total_components와 다릅니다."
        )

    component_count_total = (
        result.loaded_components
        + result.missing_components
        + result.failed_components
    )

    if (
        component_count_total
        != result.total_components
    ):
        raise RuntimeError(
            "Loaded, Missing, Failed 항목 합계가 "
            "전체 검증 항목 수와 다릅니다."
        )

    if abs(
        result.total_weight
        - 100.0
    ) > 0.001:
        raise RuntimeError(
            f"검증 가중치 합계가 100이 아닙니다: "
            f"{result.total_weight:.2f}"
        )

    if not (
        0.0
        <= result.final_score
        <= 100.0
    ):
        raise RuntimeError(
            f"최종 점수가 0~100 범위를 벗어났습니다: "
            f"{result.final_score:.2f}"
        )

    calculated_weighted_score = round(
        sum(
            float(
                component[
                    "weighted_score"
                ]
            )
            for component in result.components
        ),
        2,
    )

    if abs(
        calculated_weighted_score
        - result.earned_weighted_score
    ) > 0.01:
        raise RuntimeError(
            "개별 Weighted Score 합계와 "
            "Earned Weighted Score가 다릅니다."
        )

    expected_final_score = round(
        (
            result.earned_weighted_score
            / result.total_weight
        )
        * 100.0,
        2,
    )

    if abs(
        expected_final_score
        - result.final_score
    ) > 0.01:
        raise RuntimeError(
            "가중 점수로 다시 계산한 최종 점수와 "
            "저장된 최종 점수가 다릅니다."
        )

    valid_component_keys = {
        "out_of_sample",
        "walk_forward",
        "parameter_robustness",
        "multi_period_robustness",
        "trading_cost_stress",
        "realistic_execution",
        "execution_consistency",
    }

    result_component_keys = {
        str(
            component[
                "component_key"
            ]
        )
        for component in result.components
    }

    if (
        result_component_keys
        != valid_component_keys
    ):
        missing_keys = (
            valid_component_keys
            - result_component_keys
        )

        extra_keys = (
            result_component_keys
            - valid_component_keys
        )

        raise RuntimeError(
            "검증 항목 키 구성이 올바르지 않습니다. "
            f"Missing={sorted(missing_keys)}, "
            f"Extra={sorted(extra_keys)}"
        )

    for component in result.components:
        raw_score = float(
            component[
                "raw_score"
            ]
        )

        weight = float(
            component[
                "weight"
            ]
        )

        weighted_score = float(
            component[
                "weighted_score"
            ]
        )

        if not (
            0.0
            <= raw_score
            <= 100.0
        ):
            raise RuntimeError(
                f"{component['component_name']}의 "
                "Raw Score가 0~100 범위를 벗어났습니다."
            )

        expected_component_weighted = round(
            raw_score
            * weight
            / 100.0,
            2,
        )

        if abs(
            expected_component_weighted
            - weighted_score
        ) > 0.01:
            raise RuntimeError(
                f"{component['component_name']}의 "
                "Weighted Score 계산이 일치하지 않습니다."
            )


def validate_saved_files(
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    결과 JSON 파일이 정상 저장되었는지 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            f"시간별 Scorecard 보고서가 생성되지 않았습니다: "
            f"{report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            f"Latest Scorecard 보고서가 생성되지 않았습니다: "
            f"{latest_path}"
        )

    if report_path.stat().st_size <= 0:
        raise RuntimeError(
            "시간별 Scorecard 보고서 파일이 비어 있습니다."
        )

    if latest_path.stat().st_size <= 0:
        raise RuntimeError(
            "Latest Scorecard 보고서 파일이 비어 있습니다."
        )


def main() -> None:
    """
    V8.0 Strategy Validation Scorecard 통합 테스트입니다.

    V7.3부터 V7.9까지 생성된 latest JSON 결과를 읽고,
    가중치를 적용한 종합 점수와 검증 상태를 계산합니다.
    """

    symbol = "AAPL"

    print_test_header()

    try:
        result = run_strategy_validation_scorecard(
            symbol=symbol
        )

        (
            report_path,
            latest_path,
        ) = save_strategy_validation_scorecard(
            result
        )

        print_strategy_validation_scorecard(
            result
        )

        print_component_details(
            result
        )

        print_test_summary(
            result=result,
            report_path=report_path,
            latest_path=latest_path,
        )

        validate_scorecard_structure(
            result
        )

        validate_saved_files(
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V8.0 validation scorecard test "
            "completed successfully."
        )

        print(
            "V7.3부터 V7.9까지의 검증 결과를 "
            "하나의 종합 점수표로 통합했습니다."
        )

        print(
            "주의: 이 결과는 과거 데이터 기반 연구용 "
            "검증 결과이며 실제 투자 조언이나 "
            "미래 수익 보장이 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V8.0 Validation Scorecard "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V8.0 VALIDATION SCORECARD ERROR"
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