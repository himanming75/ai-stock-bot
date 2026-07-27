import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

from backtest.signal_engine_runtime_adapter import (
    VALID_SIGNALS,
    VALID_SIGNAL_STATUSES,
    RuntimeSignalParameters,
    SignalEngineRuntimeResult,
    convert_runtime_parameters,
    determine_runtime_signal,
    determine_signal_status,
    extract_score,
    extract_score_reasons,
    is_valid_number,
    make_json_safe,
    print_signal_engine_runtime_adapter,
    run_signal_engine_runtime_adapter,
    save_signal_engine_runtime_adapter,
    validate_market_data,
    validate_signal_parameters,
)
from backtest.trading_engine_integration import (
    TradingEngineIntegrationResult,
    run_trading_engine_integration,
    save_trading_engine_integration,
)


def print_test_header() -> None:
    """
    V9.1 Signal Engine Runtime Adapter 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V9.1 "
        "SIGNAL ENGINE RUNTIME ADAPTER TEST"
    )
    print("=" * 140)


def load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽어 Dictionary로 반환합니다.
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


def validate_parameter_structure(
    parameters: RuntimeSignalParameters,
) -> None:
    """
    RuntimeSignalParameters 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        parameters,
        RuntimeSignalParameters,
    ):
        raise RuntimeError(
            "parameters가 RuntimeSignalParameters "
            "형식이 아닙니다."
        )

    float_fields = {
        "entry_score": parameters.entry_score,
        "exit_score": parameters.exit_score,
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

    for field_name, value in float_fields.items():
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

    required_keys = {
        "entry_score",
        "exit_score",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "position_percent",
    }

    payload = parameters.to_dict()

    if set(payload.keys()) != required_keys:
        raise RuntimeError(
            "RuntimeSignalParameters.to_dict()의 구조가 "
            "예상 결과와 일치하지 않습니다."
        )


def validate_parameters_are_immutable(
    parameters: RuntimeSignalParameters,
) -> None:
    """
    RuntimeSignalParameters가 frozen Dataclass인지 검사합니다.
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
            "RuntimeSignalParameters를 직접 변경할 수 있습니다."
        )

    if (
        parameters.entry_score
        != original_entry_score
    ):
        raise RuntimeError(
            "불변 파라미터의 Entry Score가 변경되었습니다."
        )


def validate_result_structure(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    V9.1 결과 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        result,
        SignalEngineRuntimeResult,
    ):
        raise RuntimeError(
            "결과가 SignalEngineRuntimeResult 형식이 아닙니다."
        )

    if result.version != "V9.1":
        raise RuntimeError(
            f"버전이 V9.1이 아닙니다: {result.version}"
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

    if (
        result.signal_status
        not in VALID_SIGNAL_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Signal Status입니다: "
            f"{result.signal_status}"
        )

    if result.signal not in VALID_SIGNALS:
        raise RuntimeError(
            "올바르지 않은 Signal입니다: "
            f"{result.signal}"
        )

    if not result.signal_label:
        raise RuntimeError(
            "Signal Label이 비어 있습니다."
        )

    validate_parameter_structure(
        result.parameters
    )

    numeric_fields = {
        "current_score": result.current_score,
        "entry_score": result.entry_score,
        "exit_score": result.exit_score,
        "distance_to_entry": (
            result.distance_to_entry
        ),
        "distance_to_exit": (
            result.distance_to_exit
        ),
        "latest_close": result.latest_close,
    }

    for field_name, value in numeric_fields.items():
        if not is_valid_number(value):
            raise RuntimeError(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    if not result.latest_date:
        raise RuntimeError(
            "Latest Date가 비어 있습니다."
        )

    if not isinstance(
        result.score_payload,
        dict,
    ):
        raise RuntimeError(
            "Score Payload가 Dictionary가 아닙니다."
        )

    list_fields = {
        "score_reasons": result.score_reasons,
        "signal_reasons": result.signal_reasons,
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

    if not result.score_reasons:
        raise RuntimeError(
            "Score Reasons가 비어 있습니다."
        )

    if not result.signal_reasons:
        raise RuntimeError(
            "Signal Reasons가 비어 있습니다."
        )

    if not result.warnings:
        raise RuntimeError(
            "Warnings가 비어 있습니다."
        )

    if not result.next_actions:
        raise RuntimeError(
            "Next Actions가 비어 있습니다."
        )

    boolean_fields = {
        "market_data_loaded": (
            result.market_data_loaded
        ),
        "score_calculated": (
            result.score_calculated
        ),
        "runtime_parameters_applied": (
            result.runtime_parameters_applied
        ),
        "signal_generated": (
            result.signal_generated
        ),
        "signal_analysis_allowed": (
            result.signal_analysis_allowed
        ),
        "order_generated": (
            result.order_generated
        ),
        "paper_order_generated": (
            result.paper_order_generated
        ),
        "live_order_generated": (
            result.live_order_generated
        ),
        "execution_blocked": (
            result.execution_blocked
        ),
        "market_checks_passed": (
            result.market_checks_passed
        ),
        "score_checks_passed": (
            result.score_checks_passed
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

    for field_name, value in boolean_fields.items():
        if not isinstance(
            value,
            bool,
        ):
            raise RuntimeError(
                f"{field_name}가 bool 형식이 아닙니다."
            )


def validate_trading_engine_matches(
    result: SignalEngineRuntimeResult,
    trading_engine: TradingEngineIntegrationResult,
) -> None:
    """
    V9.1 결과가 V9.0 Trading Engine 설정과 일치하는지 검사합니다.
    """

    if result.symbol != trading_engine.symbol:
        raise RuntimeError(
            "V9.1 Symbol이 Trading Engine과 일치하지 않습니다."
        )

    comparisons = {
        "strategy_source": (
            result.strategy_source,
            trading_engine.strategy_source,
        ),
        "strategy_status": (
            result.strategy_status,
            trading_engine.strategy_status,
        ),
        "strategy_name": (
            result.strategy_name,
            trading_engine.strategy_name,
        ),
        "strategy_type": (
            result.strategy_type,
            trading_engine.strategy_type,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in comparisons.items():
        if actual_value != expected_value:
            raise RuntimeError(
                f"{field_name}가 Trading Engine과 "
                "일치하지 않습니다."
            )

    if (
        result.entry_score
        != trading_engine.parameters.entry_score
    ):
        raise RuntimeError(
            "Entry Score가 Trading Engine과 일치하지 않습니다."
        )

    if (
        result.exit_score
        != trading_engine.parameters.exit_score
    ):
        raise RuntimeError(
            "Exit Score가 Trading Engine과 일치하지 않습니다."
        )


def validate_parameter_conversion(
    result: SignalEngineRuntimeResult,
    trading_engine: TradingEngineIntegrationResult,
) -> None:
    """
    Trading Engine 파라미터가 Signal Runtime 파라미터로
    정확히 변환되었는지 검사합니다.
    """

    converted = convert_runtime_parameters(
        trading_engine
    )

    if converted != result.parameters:
        raise RuntimeError(
            "convert_runtime_parameters 결과가 "
            "실제 Signal 파라미터와 일치하지 않습니다."
        )

    parameter_pairs = {
        "entry_score": (
            result.parameters.entry_score,
            trading_engine.parameters.entry_score,
        ),
        "exit_score": (
            result.parameters.exit_score,
            trading_engine.parameters.exit_score,
        ),
        "stop_atr_multiple": (
            result.parameters.stop_atr_multiple,
            trading_engine.parameters.stop_atr_multiple,
        ),
        "target_atr_multiple": (
            result.parameters.target_atr_multiple,
            trading_engine.parameters.target_atr_multiple,
        ),
        "maximum_holding_days": (
            result.parameters.maximum_holding_days,
            trading_engine.parameters.maximum_holding_days,
        ),
        "position_percent": (
            result.parameters.position_percent,
            trading_engine.parameters.position_percent,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in parameter_pairs.items():
        if float(actual_value) != float(expected_value):
            raise RuntimeError(
                f"{field_name} 변환 결과가 일치하지 않습니다."
            )


def validate_signal_parameter_checks(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    Signal Runtime 파라미터 검사 결과를 확인합니다.
    """

    (
        expected_passed,
        expected_errors,
    ) = validate_signal_parameters(
        result.parameters
    )

    if (
        result.parameter_checks_passed
        != expected_passed
    ):
        raise RuntimeError(
            "Parameter Checks 결과가 실제 검사와 "
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


def validate_score_helpers(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    Score 추출 Helper 함수들을 검사합니다.
    """

    extracted_score = extract_score(
        result.score_payload
    )

    if extracted_score != result.current_score:
        raise RuntimeError(
            "extract_score 결과가 Current Score와 "
            "일치하지 않습니다."
        )

    extracted_reasons = extract_score_reasons(
        result.score_payload
    )

    if extracted_reasons != result.score_reasons:
        raise RuntimeError(
            "extract_score_reasons 결과가 "
            "Score Reasons와 일치하지 않습니다."
        )

    json_safe_payload = make_json_safe(
        result.score_payload
    )

    if not isinstance(
        json_safe_payload,
        dict,
    ):
        raise RuntimeError(
            "make_json_safe 결과가 Dictionary가 아닙니다."
        )


def validate_signal_decision(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    Current Score와 Runtime 기준점으로 생성된 Signal을 검사합니다.
    """

    (
        expected_signal,
        expected_label,
        expected_reasons,
    ) = determine_runtime_signal(
        current_score=result.current_score,
        entry_score=result.entry_score,
        exit_score=result.exit_score,
    )

    if result.signal != expected_signal:
        raise RuntimeError(
            "Signal이 점수 기준과 일치하지 않습니다. "
            f"Expected={expected_signal}, "
            f"Actual={result.signal}"
        )

    if result.signal_label != expected_label:
        raise RuntimeError(
            "Signal Label이 예상 결과와 일치하지 않습니다."
        )

    if result.signal_reasons != expected_reasons:
        raise RuntimeError(
            "Signal Reasons가 예상 결과와 일치하지 않습니다."
        )

    expected_distance_to_entry = (
        result.entry_score
        - result.current_score
    )

    expected_distance_to_exit = (
        result.current_score
        - result.exit_score
    )

    if abs(
        result.distance_to_entry
        - expected_distance_to_entry
    ) > 0.0001:
        raise RuntimeError(
            "Distance To Entry 계산이 일치하지 않습니다."
        )

    if abs(
        result.distance_to_exit
        - expected_distance_to_exit
    ) > 0.0001:
        raise RuntimeError(
            "Distance To Exit 계산이 일치하지 않습니다."
        )

    if result.current_score >= result.entry_score:
        if result.signal != "BUY":
            raise RuntimeError(
                "Current Score가 Entry 이상인데 BUY가 아닙니다."
            )

    elif result.current_score <= result.exit_score:
        if result.signal != "SELL":
            raise RuntimeError(
                "Current Score가 Exit 이하인데 SELL이 아닙니다."
            )

    else:
        if result.signal != "HOLD":
            raise RuntimeError(
                "Current Score가 Entry와 Exit 사이인데 "
                "HOLD가 아닙니다."
            )


def validate_signal_status_result(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    Signal Status 계산 결과를 검사합니다.
    """

    expected_status = determine_signal_status(
        market_checks_passed=(
            result.market_checks_passed
        ),
        score_checks_passed=(
            result.score_checks_passed
        ),
        parameter_checks_passed=(
            result.parameter_checks_passed
        ),
        permission_checks_passed=(
            result.permission_checks_passed
        ),
        signal_generated=(
            result.signal_generated
        ),
    )

    if result.signal_status != expected_status:
        raise RuntimeError(
            "Signal Status가 예상 결과와 일치하지 않습니다. "
            f"Expected={expected_status}, "
            f"Actual={result.signal_status}"
        )


def validate_execution_safety(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    V9.1에서 주문이 생성되지 않았는지 검사합니다.
    """

    if result.order_generated:
        raise RuntimeError(
            "V9.1에서 Order가 생성되었습니다."
        )

    if result.paper_order_generated:
        raise RuntimeError(
            "V9.1에서 Paper Order가 생성되었습니다."
        )

    if result.live_order_generated:
        raise RuntimeError(
            "V9.1에서 Live Order가 생성되었습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "V9.1에서 Execution Blocked가 False입니다."
        )

    execution_warning_exists = any(
        (
            "주문"
            in str(warning)
        )
        or (
            "Broker"
            in str(warning)
        )
        for warning in result.warnings
    )

    if not execution_warning_exists:
        raise RuntimeError(
            "Warnings에 주문 차단 설명이 없습니다."
        )


def validate_market_result(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    시장 데이터 및 최근 가격 결과를 검사합니다.
    """

    if not result.market_data_loaded:
        raise RuntimeError(
            "시장 데이터가 로드되지 않았습니다."
        )

    if not result.market_checks_passed:
        raise RuntimeError(
            "Market Checks가 통과되지 않았습니다."
        )

    if result.latest_close <= 0:
        raise RuntimeError(
            "Latest Close가 0 이하입니다."
        )

    if not result.latest_date:
        raise RuntimeError(
            "Latest Date가 비어 있습니다."
        )


def validate_score_result(
    result: SignalEngineRuntimeResult,
) -> None:
    """
    점수 계산 결과를 검사합니다.
    """

    if not result.score_calculated:
        raise RuntimeError(
            "Score Calculated가 False입니다."
        )

    if not result.score_checks_passed:
        raise RuntimeError(
            "Score Checks가 통과되지 않았습니다."
        )

    if not (
        0.0
        <= result.current_score
        <= 100.0
    ):
        raise RuntimeError(
            "Current Score가 0~100 범위를 벗어났습니다."
        )

    if not result.runtime_parameters_applied:
        raise RuntimeError(
            "Runtime Parameters가 적용되지 않았습니다."
        )

    if not result.signal_generated:
        raise RuntimeError(
            "Signal이 생성되지 않았습니다."
        )

    if result.signal_status != "READY":
        raise RuntimeError(
            "정상 신호인데 Signal Status가 READY가 아닙니다."
        )


def validate_saved_files(
    result: SignalEngineRuntimeResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.1 JSON 저장 결과를 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            f"V9.1 Report 파일이 없습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            f"V9.1 Latest 파일이 없습니다: {latest_path}"
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "V9.1 Report와 Latest 파일 내용이 "
            "일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_trading_engine_file",
        "signal_status",
        "signal",
        "signal_label",
        "current_score",
        "entry_score",
        "exit_score",
        "distance_to_entry",
        "distance_to_exit",
        "latest_date",
        "latest_close",
        "strategy_source",
        "strategy_status",
        "strategy_name",
        "strategy_type",
        "parameters",
        "score_payload",
        "score_reasons",
        "signal_reasons",
        "market_data_loaded",
        "score_calculated",
        "runtime_parameters_applied",
        "signal_generated",
        "signal_analysis_allowed",
        "order_generated",
        "paper_order_generated",
        "live_order_generated",
        "execution_blocked",
        "market_checks_passed",
        "score_checks_passed",
        "parameter_checks_passed",
        "permission_checks_passed",
        "all_checks_passed",
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
            "저장된 V9.1 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    text_checks = {
        "version": result.version,
        "symbol": result.symbol,
        "signal_status": (
            result.signal_status
        ),
        "signal": result.signal,
        "signal_label": result.signal_label,
        "latest_date": result.latest_date,
        "strategy_source": (
            result.strategy_source
        ),
        "strategy_status": (
            result.strategy_status
        ),
    }

    for field_name, expected_value in text_checks.items():
        if (
            str(report_payload.get(field_name))
            != str(expected_value)
        ):
            raise RuntimeError(
                f"저장된 {field_name} 값이 실행 결과와 "
                "일치하지 않습니다."
            )

    numeric_checks = {
        "current_score": (
            result.current_score
        ),
        "entry_score": result.entry_score,
        "exit_score": result.exit_score,
        "distance_to_entry": (
            result.distance_to_entry
        ),
        "distance_to_exit": (
            result.distance_to_exit
        ),
        "latest_close": result.latest_close,
    }

    for field_name, expected_value in (
        numeric_checks.items()
    ):
        actual_value = report_payload.get(
            field_name
        )

        if not is_valid_number(actual_value):
            raise RuntimeError(
                f"저장된 {field_name}가 유효한 숫자가 아닙니다."
            )

        if abs(
            float(actual_value)
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"저장된 {field_name} 값이 실행 결과와 "
                "일치하지 않습니다."
            )

    boolean_checks = {
        "market_data_loaded": (
            result.market_data_loaded
        ),
        "score_calculated": (
            result.score_calculated
        ),
        "runtime_parameters_applied": (
            result.runtime_parameters_applied
        ),
        "signal_generated": (
            result.signal_generated
        ),
        "signal_analysis_allowed": (
            result.signal_analysis_allowed
        ),
        "order_generated": (
            result.order_generated
        ),
        "paper_order_generated": (
            result.paper_order_generated
        ),
        "live_order_generated": (
            result.live_order_generated
        ),
        "execution_blocked": (
            result.execution_blocked
        ),
        "market_checks_passed": (
            result.market_checks_passed
        ),
        "score_checks_passed": (
            result.score_checks_passed
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
        if (
            report_payload.get(field_name)
            is not expected_value
        ):
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
            "저장된 Parameters가 Dictionary가 아닙니다."
        )

    if (
        saved_parameters
        != result.parameters.to_dict()
    ):
        raise RuntimeError(
            "저장된 Parameters가 실행 결과와 일치하지 않습니다."
        )

    list_checks = {
        "score_reasons": result.score_reasons,
        "signal_reasons": result.signal_reasons,
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

    if (
        Path(str(report_payload["report_path"]))
        != report_path
    ):
        raise RuntimeError(
            "JSON 내부 Report Path가 실제 경로와 "
            "일치하지 않습니다."
        )

    if (
        Path(str(report_payload["latest_path"]))
        != latest_path
    ):
        raise RuntimeError(
            "JSON 내부 Latest Path가 실제 경로와 "
            "일치하지 않습니다."
        )


def print_test_result(
    result: SignalEngineRuntimeResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.1 최종 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V9.1 SIGNAL ENGINE RUNTIME ADAPTER "
        "TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

    print(
        f"Signal status                  : "
        f"{result.signal_status}"
    )

    print(
        f"Signal                         : "
        f"{result.signal}"
    )

    print(
        f"Signal label                   : "
        f"{result.signal_label}"
    )

    print()
    print("MARKET")
    print("-" * 140)

    print(
        f"Latest date                    : "
        f"{result.latest_date}"
    )

    print(
        f"Latest close                   : "
        f"${result.latest_close:,.2f}"
    )

    print()
    print("SCORE")
    print("-" * 140)

    print(
        f"Current score                  : "
        f"{result.current_score:.2f}"
    )

    print(
        f"Entry score                    : "
        f"{result.entry_score:.2f}"
    )

    print(
        f"Exit score                     : "
        f"{result.exit_score:.2f}"
    )

    print(
        f"Distance to entry              : "
        f"{result.distance_to_entry:+.2f}"
    )

    print(
        f"Distance from exit             : "
        f"{result.distance_to_exit:+.2f}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Signal analysis allowed        : "
        f"{result.signal_analysis_allowed}"
    )

    print(
        f"Order generated                : "
        f"{result.order_generated}"
    )

    print(
        f"Paper order generated          : "
        f"{result.paper_order_generated}"
    )

    print(
        f"Live order generated           : "
        f"{result.live_order_generated}"
    )

    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
    )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Market checks passed           : "
        f"{result.market_checks_passed}"
    )

    print(
        f"Score checks passed            : "
        f"{result.score_checks_passed}"
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
        f"Runtime parameters applied     : "
        f"{result.runtime_parameters_applied}"
    )

    print(
        f"Signal generated               : "
        f"{result.signal_generated}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Trading Engine file     : "
        f"{result.source_trading_engine_file}"
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
    result: SignalEngineRuntimeResult,
    trading_engine: TradingEngineIntegrationResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True/False로 출력합니다.
    """

    source_engine_path = (
        Path(result.source_trading_engine_file)
        if result.source_trading_engine_file
        else None
    )

    expected_signal, _, _ = (
        determine_runtime_signal(
            current_score=result.current_score,
            entry_score=result.entry_score,
            exit_score=result.exit_score,
        )
    )

    checks = {
        "Version is V9.1": (
            result.version == "V9.1"
        ),
        "Signal status is valid": (
            result.signal_status
            in VALID_SIGNAL_STATUSES
        ),
        "Signal is valid": (
            result.signal
            in VALID_SIGNALS
        ),
        "Symbol matches engine": (
            result.symbol
            == trading_engine.symbol
        ),
        "Strategy source matches": (
            result.strategy_source
            == trading_engine.strategy_source
        ),
        "Strategy status matches": (
            result.strategy_status
            == trading_engine.strategy_status
        ),
        "Entry score matches": (
            result.entry_score
            == trading_engine.parameters.entry_score
        ),
        "Exit score matches": (
            result.exit_score
            == trading_engine.parameters.exit_score
        ),
        "Market data loaded": (
            result.market_data_loaded
        ),
        "Market checks passed": (
            result.market_checks_passed
        ),
        "Score calculated": (
            result.score_calculated
        ),
        "Score checks passed": (
            result.score_checks_passed
        ),
        "Current score is valid": (
            0.0
            <= result.current_score
            <= 100.0
        ),
        "Signal matches score": (
            result.signal
            == expected_signal
        ),
        "Runtime parameters applied": (
            result.runtime_parameters_applied
        ),
        "Signal generated": (
            result.signal_generated
        ),
        "Signal analysis allowed": (
            result.signal_analysis_allowed
        ),
        "Order generation blocked": (
            not result.order_generated
        ),
        "Paper order blocked": (
            not result.paper_order_generated
        ),
        "Live order blocked": (
            not result.live_order_generated
        ),
        "Execution blocked": (
            result.execution_blocked
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
        "Parameters are immutable": True,
        "Score payload exists": bool(
            result.score_payload
        ),
        "Score reasons exist": bool(
            result.score_reasons
        ),
        "Signal reasons exist": bool(
            result.signal_reasons
        ),
        "Warnings exist": bool(
            result.warnings
        ),
        "Next actions exist": bool(
            result.next_actions
        ),
        "Source engine file exists": (
            source_engine_path.exists()
            if source_engine_path
            else False
        ),
        "Report file exists": (
            report_path.exists()
        ),
        "Latest file exists": (
            latest_path.exists()
        ),
    }

    print()
    print("=" * 140)
    print("VALIDATION CHECKS")
    print("=" * 140)

    for check_name, check_result in checks.items():
        print(
            f"{check_name:<36}: {check_result}"
        )

    print("=" * 140)


def main() -> None:
    """
    V9.1 Signal Engine Runtime Adapter 통합 테스트입니다.
    """

    symbol = "AAPL"

    print_test_header()

    try:
        trading_engine = (
            run_trading_engine_integration(
                symbol=symbol,
            )
        )

        (
            engine_report_path,
            engine_latest_path,
        ) = save_trading_engine_integration(
            trading_engine
        )

        if not engine_report_path.exists():
            raise RuntimeError(
                "V9.0 Trading Engine Report 파일이 없습니다."
            )

        if not engine_latest_path.exists():
            raise RuntimeError(
                "V9.0 Trading Engine Latest 파일이 없습니다."
            )

        result = (
            run_signal_engine_runtime_adapter(
                symbol=symbol,
                period="5y",
                interval="1d",
                trading_engine=trading_engine,
            )
        )

        (
            report_path,
            latest_path,
        ) = save_signal_engine_runtime_adapter(
            result
        )

        print_signal_engine_runtime_adapter(
            result
        )

        validate_result_structure(
            result
        )

        validate_parameters_are_immutable(
            result.parameters
        )

        validate_trading_engine_matches(
            result=result,
            trading_engine=trading_engine,
        )

        validate_parameter_conversion(
            result=result,
            trading_engine=trading_engine,
        )

        validate_signal_parameter_checks(
            result
        )

        validate_score_helpers(
            result
        )

        validate_signal_decision(
            result
        )

        validate_signal_status_result(
            result
        )

        validate_execution_safety(
            result
        )

        validate_market_result(
            result
        )

        validate_score_result(
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
            trading_engine=trading_engine,
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V9.1 signal engine runtime adapter "
            "test completed successfully."
        )

        print(
            f"현재 {result.symbol} 점수는 "
            f"{result.current_score:.2f}이고 "
            f"Runtime 신호는 {result.signal}입니다."
        )

        print(
            "V9.0 Trading Engine 파라미터가 "
            "V9.1 Signal Engine에 정상적으로 전달되었습니다."
        )

        print(
            "BUY/HOLD/SELL 분석 신호만 생성되었으며 "
            "모의 주문과 실거래 주문은 모두 차단되었습니다."
        )

        print(
            "주의: 이 테스트는 시장 데이터 기반 분석 신호만 "
            "검증하며 실제 증권 주문이나 자동 매매를 "
            "실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V9.1 Signal Engine 테스트를 "
            "중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V9.1 SIGNAL ENGINE RUNTIME ADAPTER ERROR"
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