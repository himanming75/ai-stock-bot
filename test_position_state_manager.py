import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

from backtest.position_state_manager import (
    VALID_MANAGER_STATUSES,
    VALID_POSITION_ACTIONS,
    VALID_POSITION_STATES,
    CurrentPosition,
    PositionStateResult,
    determine_manager_status,
    determine_position_action,
    normalize_position,
    print_position_state_manager,
    run_position_state_manager,
    save_position_state_manager,
    validate_position,
    validate_signal_result,
    validate_transition,
)
from backtest.signal_engine_runtime_adapter import (
    SignalEngineRuntimeResult,
    run_signal_engine_runtime_adapter,
    save_signal_engine_runtime_adapter,
)
from backtest.trading_engine_integration import (
    run_trading_engine_integration,
    save_trading_engine_integration,
)


def print_test_header() -> None:
    """
    V9.2 Position State Manager 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V9.2 "
        "POSITION STATE MANAGER TEST"
    )
    print("=" * 140)


def load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽고 Dictionary로 반환합니다.
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


def validate_current_position_structure(
    position: CurrentPosition,
) -> None:
    """
    CurrentPosition 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        position,
        CurrentPosition,
    ):
        raise RuntimeError(
            "current_position이 CurrentPosition 형식이 아닙니다."
        )

    if position.state not in VALID_POSITION_STATES:
        raise RuntimeError(
            f"올바르지 않은 Position State입니다: "
            f"{position.state}"
        )

    if not isinstance(
        position.shares,
        int,
    ):
        raise RuntimeError(
            "Shares가 int 형식이 아닙니다."
        )

    if not isinstance(
        position.average_price,
        float,
    ):
        raise RuntimeError(
            "Average Price가 float 형식이 아닙니다."
        )

    if not isinstance(
        position.holding_days,
        int,
    ):
        raise RuntimeError(
            "Holding Days가 int 형식이 아닙니다."
        )

    payload = position.to_dict()

    required_keys = {
        "state",
        "shares",
        "average_price",
        "entry_date",
        "holding_days",
    }

    if set(payload.keys()) != required_keys:
        raise RuntimeError(
            "CurrentPosition.to_dict() 구조가 "
            "예상 결과와 일치하지 않습니다."
        )


def validate_current_position_is_immutable(
    position: CurrentPosition,
) -> None:
    """
    CurrentPosition이 frozen Dataclass인지 검사합니다.
    """

    original_state = position.state

    immutable = False

    try:
        position.state = "LONG"

    except (
        FrozenInstanceError,
        AttributeError,
    ):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "CurrentPosition 값을 직접 변경할 수 있습니다."
        )

    if position.state != original_state:
        raise RuntimeError(
            "불변 CurrentPosition 상태가 변경되었습니다."
        )


def validate_result_structure(
    result: PositionStateResult,
) -> None:
    """
    V9.2 결과 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        result,
        PositionStateResult,
    ):
        raise RuntimeError(
            "결과가 PositionStateResult 형식이 아닙니다."
        )

    if result.version != "V9.2":
        raise RuntimeError(
            f"버전이 V9.2가 아닙니다: {result.version}"
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

    if result.manager_status not in VALID_MANAGER_STATUSES:
        raise RuntimeError(
            "올바르지 않은 Manager Status입니다: "
            f"{result.manager_status}"
        )

    if result.position_state not in VALID_POSITION_STATES:
        raise RuntimeError(
            "올바르지 않은 Position State입니다: "
            f"{result.position_state}"
        )

    if (
        result.recommended_action
        not in VALID_POSITION_ACTIONS
    ):
        raise RuntimeError(
            "올바르지 않은 Recommended Action입니다: "
            f"{result.recommended_action}"
        )

    if result.signal not in {
        "BUY",
        "HOLD",
        "SELL",
    }:
        raise RuntimeError(
            f"올바르지 않은 Signal입니다: {result.signal}"
        )

    if not result.action_label:
        raise RuntimeError(
            "Action Label이 비어 있습니다."
        )

    validate_current_position_structure(
        result.current_position
    )

    numeric_fields = {
        "current_score": result.current_score,
        "entry_score": result.entry_score,
        "exit_score": result.exit_score,
        "latest_close": result.latest_close,
        "position_percent": (
            result.position_percent
        ),
    }

    for field_name, value in numeric_fields.items():
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

    boolean_fields = {
        "action_required": result.action_required,
        "holding_limit_reached": (
            result.holding_limit_reached
        ),
        "signal_result_loaded": (
            result.signal_result_loaded
        ),
        "position_loaded": result.position_loaded,
        "position_valid": result.position_valid,
        "signal_valid": result.signal_valid,
        "transition_valid": (
            result.transition_valid
        ),
        "action_generated": result.action_generated,
        "order_generated": result.order_generated,
        "paper_order_generated": (
            result.paper_order_generated
        ),
        "live_order_generated": (
            result.live_order_generated
        ),
        "execution_blocked": (
            result.execution_blocked
        ),
        "manual_approval_required": (
            result.manual_approval_required
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

    list_fields = {
        "reasons": result.reasons,
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


def validate_signal_matches(
    result: PositionStateResult,
    signal_result: SignalEngineRuntimeResult,
) -> None:
    """
    Position State 결과가 V9.1 Signal 결과와 일치하는지 검사합니다.
    """

    if result.symbol != signal_result.symbol:
        raise RuntimeError(
            "V9.2 Symbol이 V9.1 Signal Result와 "
            "일치하지 않습니다."
        )

    if result.signal != signal_result.signal:
        raise RuntimeError(
            "V9.2 Signal이 V9.1 Signal과 일치하지 않습니다."
        )

    comparisons = {
        "current_score": (
            result.current_score,
            signal_result.current_score,
        ),
        "entry_score": (
            result.entry_score,
            signal_result.entry_score,
        ),
        "exit_score": (
            result.exit_score,
            signal_result.exit_score,
        ),
        "latest_close": (
            result.latest_close,
            signal_result.latest_close,
        ),
        "position_percent": (
            result.position_percent,
            signal_result.parameters.position_percent,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in comparisons.items():
        if abs(
            float(actual_value)
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"{field_name}가 V9.1 Signal Result와 "
                "일치하지 않습니다."
            )

    if (
        result.latest_date
        != signal_result.latest_date
    ):
        raise RuntimeError(
            "Latest Date가 V9.1 Signal Result와 "
            "일치하지 않습니다."
        )

    if (
        result.maximum_holding_days
        != signal_result.parameters.maximum_holding_days
    ):
        raise RuntimeError(
            "Maximum Holding Days가 Signal Result와 "
            "일치하지 않습니다."
        )

    strategy_checks = {
        "strategy_source": (
            result.strategy_source,
            signal_result.strategy_source,
        ),
        "strategy_status": (
            result.strategy_status,
            signal_result.strategy_status,
        ),
        "strategy_name": (
            result.strategy_name,
            signal_result.strategy_name,
        ),
        "strategy_type": (
            result.strategy_type,
            signal_result.strategy_type,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in strategy_checks.items():
        if actual_value != expected_value:
            raise RuntimeError(
                f"{field_name}가 Signal Result와 "
                "일치하지 않습니다."
            )


def validate_position_helper(
    position: CurrentPosition,
) -> None:
    """
    normalize_position과 validate_position을 검사합니다.
    """

    normalized = normalize_position(
        position
    )

    if normalized != position:
        raise RuntimeError(
            "이미 정상화된 Position이 normalize_position 후 "
            "변경되었습니다."
        )

    (
        position_valid,
        position_errors,
    ) = validate_position(
        normalized
    )

    if not position_valid:
        raise RuntimeError(
            "정상 Position이 validate_position을 "
            f"통과하지 못했습니다: {position_errors}"
        )

    if position_errors:
        raise RuntimeError(
            "정상 Position 검사에서 Error가 생성되었습니다."
        )


def validate_default_flat_position() -> None:
    """
    Position이 없는 경우 기본 FLAT 상태가 생성되는지 검사합니다.
    """

    position = normalize_position(
        None
    )

    if position.state != "FLAT":
        raise RuntimeError(
            "기본 Position State가 FLAT이 아닙니다."
        )

    if position.shares != 0:
        raise RuntimeError(
            "기본 FLAT Position의 Shares가 0이 아닙니다."
        )

    if position.average_price != 0.0:
        raise RuntimeError(
            "기본 FLAT Position의 Average Price가 "
            "0이 아닙니다."
        )

    if position.entry_date is not None:
        raise RuntimeError(
            "기본 FLAT Position의 Entry Date가 "
            "None이 아닙니다."
        )

    if position.holding_days != 0:
        raise RuntimeError(
            "기본 FLAT Position의 Holding Days가 "
            "0이 아닙니다."
        )


def validate_signal_helper(
    signal_result: SignalEngineRuntimeResult,
) -> None:
    """
    validate_signal_result Helper를 검사합니다.
    """

    (
        signal_valid,
        signal_errors,
    ) = validate_signal_result(
        signal_result
    )

    if not signal_valid:
        raise RuntimeError(
            "정상 V9.1 Signal Result가 검사에 실패했습니다: "
            f"{signal_errors}"
        )

    if signal_errors:
        raise RuntimeError(
            "정상 Signal Result 검사에서 Error가 생성되었습니다."
        )


def validate_expected_action(
    result: PositionStateResult,
) -> None:
    """
    현재 Position과 Signal 조합으로 예상 행동을 계산합니다.
    """

    (
        expected_action,
        expected_label,
        expected_required,
        expected_reasons,
    ) = determine_position_action(
        position_state=result.position_state,
        signal=result.signal,
        holding_limit_reached=(
            result.holding_limit_reached
        ),
    )

    if result.recommended_action != expected_action:
        raise RuntimeError(
            "Recommended Action이 예상 결과와 "
            "일치하지 않습니다. "
            f"Expected={expected_action}, "
            f"Actual={result.recommended_action}"
        )

    if result.action_label != expected_label:
        raise RuntimeError(
            "Action Label이 예상 결과와 일치하지 않습니다."
        )

    if result.action_required != expected_required:
        raise RuntimeError(
            "Action Required가 예상 결과와 일치하지 않습니다."
        )

    if result.reasons != expected_reasons:
        raise RuntimeError(
            "Reasons가 예상 결과와 일치하지 않습니다."
        )


def validate_transition_result(
    result: PositionStateResult,
) -> None:
    """
    Position 상태와 추천 행동의 전환 규칙을 검사합니다.
    """

    (
        expected_valid,
        expected_errors,
    ) = validate_transition(
        position_state=result.position_state,
        action=result.recommended_action,
    )

    if result.transition_valid != expected_valid:
        raise RuntimeError(
            "Transition Valid 결과가 실제 검사와 "
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
                    "Transition Error가 Warnings에 없습니다: "
                    f"{error_message}"
                )


def validate_manager_status_result(
    result: PositionStateResult,
) -> None:
    """
    Manager Status 계산 결과를 검사합니다.
    """

    expected_status = determine_manager_status(
        signal_valid=result.signal_valid,
        position_valid=result.position_valid,
        transition_valid=result.transition_valid,
        action_generated=result.action_generated,
    )

    if result.manager_status != expected_status:
        raise RuntimeError(
            "Manager Status가 예상 결과와 일치하지 않습니다. "
            f"Expected={expected_status}, "
            f"Actual={result.manager_status}"
        )


def validate_flat_action_rules() -> None:
    """
    FLAT 상태에서 BUY/HOLD/SELL 행동 규칙을 검사합니다.
    """

    test_cases = [
        {
            "signal": "BUY",
            "expected_action": "ENTER_LONG",
            "expected_required": True,
        },
        {
            "signal": "HOLD",
            "expected_action": "NO_ACTION",
            "expected_required": False,
        },
        {
            "signal": "SELL",
            "expected_action": "NO_ACTION",
            "expected_required": False,
        },
    ]

    for test_case in test_cases:
        (
            action,
            _,
            action_required,
            reasons,
        ) = determine_position_action(
            position_state="FLAT",
            signal=test_case["signal"],
            holding_limit_reached=False,
        )

        if action != test_case["expected_action"]:
            raise RuntimeError(
                "FLAT 상태 행동 규칙이 일치하지 않습니다. "
                f"Signal={test_case['signal']}, "
                f"Expected={test_case['expected_action']}, "
                f"Actual={action}"
            )

        if (
            action_required
            != test_case["expected_required"]
        ):
            raise RuntimeError(
                "FLAT 상태 Action Required 결과가 "
                "일치하지 않습니다."
            )

        if not reasons:
            raise RuntimeError(
                "FLAT 상태 행동 판단 Reasons가 비어 있습니다."
            )


def validate_long_action_rules() -> None:
    """
    LONG 상태에서 BUY/HOLD/SELL 행동 규칙을 검사합니다.
    """

    test_cases = [
        {
            "signal": "BUY",
            "expected_action": "HOLD_POSITION",
            "expected_required": False,
        },
        {
            "signal": "HOLD",
            "expected_action": "HOLD_POSITION",
            "expected_required": False,
        },
        {
            "signal": "SELL",
            "expected_action": "EXIT_LONG",
            "expected_required": True,
        },
    ]

    for test_case in test_cases:
        (
            action,
            _,
            action_required,
            reasons,
        ) = determine_position_action(
            position_state="LONG",
            signal=test_case["signal"],
            holding_limit_reached=False,
        )

        if action != test_case["expected_action"]:
            raise RuntimeError(
                "LONG 상태 행동 규칙이 일치하지 않습니다. "
                f"Signal={test_case['signal']}, "
                f"Expected={test_case['expected_action']}, "
                f"Actual={action}"
            )

        if (
            action_required
            != test_case["expected_required"]
        ):
            raise RuntimeError(
                "LONG 상태 Action Required 결과가 "
                "일치하지 않습니다."
            )

        if not reasons:
            raise RuntimeError(
                "LONG 상태 행동 판단 Reasons가 비어 있습니다."
            )


def validate_holding_limit_rule() -> None:
    """
    최대 보유기간 도달 시 EXIT_LONG이 생성되는지 검사합니다.
    """

    for signal in [
        "BUY",
        "HOLD",
        "SELL",
    ]:
        (
            action,
            label,
            action_required,
            reasons,
        ) = determine_position_action(
            position_state="LONG",
            signal=signal,
            holding_limit_reached=True,
        )

        if action != "EXIT_LONG":
            raise RuntimeError(
                "최대 보유기간 도달 시 EXIT_LONG이 "
                f"생성되지 않았습니다. Signal={signal}"
            )

        if not action_required:
            raise RuntimeError(
                "최대 보유기간 도달 시 Action Required가 "
                "False입니다."
            )

        if not label:
            raise RuntimeError(
                "최대 보유기간 Action Label이 비어 있습니다."
            )

        if not reasons:
            raise RuntimeError(
                "최대 보유기간 Reasons가 비어 있습니다."
            )


def validate_invalid_action_rules() -> None:
    """
    잘못된 Position 또는 Signal이 BLOCKED되는지 검사합니다.
    """

    invalid_cases = [
        {
            "position": "SHORT",
            "signal": "BUY",
        },
        {
            "position": "FLAT",
            "signal": "INVALID",
        },
        {
            "position": "UNKNOWN",
            "signal": "UNKNOWN",
        },
    ]

    for test_case in invalid_cases:
        (
            action,
            _,
            action_required,
            reasons,
        ) = determine_position_action(
            position_state=test_case["position"],
            signal=test_case["signal"],
            holding_limit_reached=False,
        )

        if action != "BLOCKED":
            raise RuntimeError(
                "잘못된 Position 또는 Signal이 "
                "BLOCKED되지 않았습니다."
            )

        if action_required:
            raise RuntimeError(
                "BLOCKED 행동의 Action Required가 True입니다."
            )

        if not reasons:
            raise RuntimeError(
                "BLOCKED 행동의 Reasons가 비어 있습니다."
            )


def validate_execution_safety(
    result: PositionStateResult,
) -> None:
    """
    V9.2에서 주문이 생성되지 않았는지 검사합니다.
    """

    if result.order_generated:
        raise RuntimeError(
            "V9.2에서 실제 Order가 생성되었습니다."
        )

    if result.paper_order_generated:
        raise RuntimeError(
            "V9.2에서 Paper Order가 생성되었습니다."
        )

    if result.live_order_generated:
        raise RuntimeError(
            "V9.2에서 Live Order가 생성되었습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "V9.2에서 Execution Blocked가 False입니다."
        )

    if not result.manual_approval_required:
        raise RuntimeError(
            "Manual Approval Required가 False입니다."
        )

    safety_warning_exists = any(
        (
            "주문"
            in str(warning)
        )
        or (
            "Broker"
            in str(warning)
        )
        or (
            "차단"
            in str(warning)
        )
        for warning in result.warnings
    )

    if not safety_warning_exists:
        raise RuntimeError(
            "Warnings에 주문 차단 관련 설명이 없습니다."
        )


def validate_default_flat_result(
    result: PositionStateResult,
) -> None:
    """
    기본 실행 시 FLAT 포지션 결과를 검사합니다.
    """

    if result.position_state != "FLAT":
        raise RuntimeError(
            "기본 실행 Position State가 FLAT이 아닙니다."
        )

    if result.current_position.shares != 0:
        raise RuntimeError(
            "기본 FLAT 포지션 Shares가 0이 아닙니다."
        )

    if result.current_position.average_price != 0.0:
        raise RuntimeError(
            "기본 FLAT 포지션 Average Price가 0이 아닙니다."
        )

    if result.current_position.holding_days != 0:
        raise RuntimeError(
            "기본 FLAT 포지션 Holding Days가 0이 아닙니다."
        )

    if result.signal == "BUY":
        expected_action = "ENTER_LONG"

    else:
        expected_action = "NO_ACTION"

    if result.recommended_action != expected_action:
        raise RuntimeError(
            "기본 FLAT 상태 Recommended Action이 "
            "예상 결과와 일치하지 않습니다. "
            f"Signal={result.signal}, "
            f"Expected={expected_action}, "
            f"Actual={result.recommended_action}"
        )


def validate_long_position_scenario(
    signal_result: SignalEngineRuntimeResult,
) -> PositionStateResult:
    """
    LONG 상태 시나리오를 별도로 실행하고 검사합니다.
    """

    long_position = CurrentPosition(
        state="LONG",
        shares=10,
        average_price=150.00,
        entry_date="2026-07-01",
        holding_days=5,
    )

    result = run_position_state_manager(
        symbol=signal_result.symbol,
        current_position=long_position,
        signal_result=signal_result,
    )

    if result.position_state != "LONG":
        raise RuntimeError(
            "LONG 시나리오 Position State가 LONG이 아닙니다."
        )

    if result.current_position.shares != 10:
        raise RuntimeError(
            "LONG 시나리오 Shares가 일치하지 않습니다."
        )

    if result.current_position.average_price != 150.00:
        raise RuntimeError(
            "LONG 시나리오 Average Price가 일치하지 않습니다."
        )

    expected_action_map = {
        "BUY": "HOLD_POSITION",
        "HOLD": "HOLD_POSITION",
        "SELL": "EXIT_LONG",
    }

    expected_action = expected_action_map[
        signal_result.signal
    ]

    if result.recommended_action != expected_action:
        raise RuntimeError(
            "LONG 시나리오 Recommended Action이 "
            "예상 결과와 일치하지 않습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "LONG 시나리오 All Checks Passed가 False입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_holding_limit_scenario(
    signal_result: SignalEngineRuntimeResult,
) -> PositionStateResult:
    """
    최대 보유기간 도달 시나리오를 실행하고 검사합니다.
    """

    holding_limit_position = CurrentPosition(
        state="LONG",
        shares=10,
        average_price=150.00,
        entry_date="2026-06-01",
        holding_days=(
            signal_result
            .parameters
            .maximum_holding_days
        ),
    )

    result = run_position_state_manager(
        symbol=signal_result.symbol,
        current_position=holding_limit_position,
        signal_result=signal_result,
    )

    if not result.holding_limit_reached:
        raise RuntimeError(
            "Holding Limit Reached가 False입니다."
        )

    if result.recommended_action != "EXIT_LONG":
        raise RuntimeError(
            "최대 보유기간 시나리오에서 EXIT_LONG이 "
            "생성되지 않았습니다."
        )

    if not result.action_required:
        raise RuntimeError(
            "최대 보유기간 시나리오에서 Action Required가 "
            "False입니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "최대 보유기간 시나리오 All Checks Passed가 "
            "False입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_saved_files(
    result: PositionStateResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.2 JSON 저장 결과를 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            f"V9.2 Report 파일이 없습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            f"V9.2 Latest 파일이 없습니다: {latest_path}"
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "V9.2 Report와 Latest 파일 내용이 "
            "일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_signal_file",
        "manager_status",
        "position_state",
        "signal",
        "recommended_action",
        "action_label",
        "action_required",
        "current_position",
        "current_score",
        "entry_score",
        "exit_score",
        "latest_close",
        "latest_date",
        "strategy_source",
        "strategy_status",
        "strategy_name",
        "strategy_type",
        "maximum_holding_days",
        "position_percent",
        "holding_limit_reached",
        "signal_result_loaded",
        "position_loaded",
        "position_valid",
        "signal_valid",
        "transition_valid",
        "action_generated",
        "order_generated",
        "paper_order_generated",
        "live_order_generated",
        "execution_blocked",
        "manual_approval_required",
        "all_checks_passed",
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
            "저장된 V9.2 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    text_checks = {
        "version": result.version,
        "symbol": result.symbol,
        "manager_status": (
            result.manager_status
        ),
        "position_state": (
            result.position_state
        ),
        "signal": result.signal,
        "recommended_action": (
            result.recommended_action
        ),
        "action_label": result.action_label,
        "latest_date": result.latest_date,
        "strategy_source": (
            result.strategy_source
        ),
        "strategy_status": (
            result.strategy_status
        ),
    }

    for field_name, expected_value in text_checks.items():
        actual_value = report_payload.get(
            field_name
        )

        if str(actual_value) != str(expected_value):
            raise RuntimeError(
                f"저장된 {field_name} 값이 실행 결과와 "
                "일치하지 않습니다."
            )

    numeric_checks = {
        "current_score": result.current_score,
        "entry_score": result.entry_score,
        "exit_score": result.exit_score,
        "latest_close": result.latest_close,
        "position_percent": (
            result.position_percent
        ),
    }

    for field_name, expected_value in (
        numeric_checks.items()
    ):
        actual_value = report_payload.get(
            field_name
        )

        try:
            numeric_value = float(
                actual_value
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise RuntimeError(
                f"저장된 {field_name}가 숫자가 아닙니다."
            ) from error

        if abs(
            numeric_value
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"저장된 {field_name} 값이 실행 결과와 "
                "일치하지 않습니다."
            )

    integer_checks = {
        "maximum_holding_days": (
            result.maximum_holding_days
        ),
    }

    for field_name, expected_value in (
        integer_checks.items()
    ):
        if int(
            report_payload.get(field_name)
        ) != int(expected_value):
            raise RuntimeError(
                f"저장된 {field_name} 값이 실행 결과와 "
                "일치하지 않습니다."
            )

    boolean_checks = {
        "action_required": (
            result.action_required
        ),
        "holding_limit_reached": (
            result.holding_limit_reached
        ),
        "signal_result_loaded": (
            result.signal_result_loaded
        ),
        "position_loaded": (
            result.position_loaded
        ),
        "position_valid": (
            result.position_valid
        ),
        "signal_valid": result.signal_valid,
        "transition_valid": (
            result.transition_valid
        ),
        "action_generated": (
            result.action_generated
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
        "manual_approval_required": (
            result.manual_approval_required
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

    saved_position = report_payload.get(
        "current_position"
    )

    if not isinstance(
        saved_position,
        dict,
    ):
        raise RuntimeError(
            "저장된 Current Position이 Dictionary가 아닙니다."
        )

    if (
        saved_position
        != result.current_position.to_dict()
    ):
        raise RuntimeError(
            "저장된 Current Position이 실행 결과와 "
            "일치하지 않습니다."
        )

    list_checks = {
        "reasons": result.reasons,
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
    result: PositionStateResult,
    long_result: PositionStateResult,
    holding_limit_result: PositionStateResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.2 최종 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V9.2 POSITION STATE MANAGER "
        "TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

    print(
        f"Manager status                 : "
        f"{result.manager_status}"
    )

    print(
        f"Signal                         : "
        f"{result.signal}"
    )

    print()
    print("DEFAULT FLAT SCENARIO")
    print("-" * 140)

    print(
        f"Position state                 : "
        f"{result.position_state}"
    )

    print(
        f"Recommended action             : "
        f"{result.recommended_action}"
    )

    print(
        f"Action required                : "
        f"{result.action_required}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("LONG POSITION SCENARIO")
    print("-" * 140)

    print(
        f"Position state                 : "
        f"{long_result.position_state}"
    )

    print(
        f"Shares                         : "
        f"{long_result.current_position.shares}"
    )

    print(
        f"Holding days                   : "
        f"{long_result.current_position.holding_days}"
    )

    print(
        f"Recommended action             : "
        f"{long_result.recommended_action}"
    )

    print(
        f"All checks passed              : "
        f"{long_result.all_checks_passed}"
    )

    print()
    print("HOLDING LIMIT SCENARIO")
    print("-" * 140)

    print(
        f"Holding days                   : "
        f"{holding_limit_result.current_position.holding_days}"
    )

    print(
        f"Maximum holding days           : "
        f"{holding_limit_result.maximum_holding_days}"
    )

    print(
        f"Holding limit reached          : "
        f"{holding_limit_result.holding_limit_reached}"
    )

    print(
        f"Recommended action             : "
        f"{holding_limit_result.recommended_action}"
    )

    print(
        f"Action required                : "
        f"{holding_limit_result.action_required}"
    )

    print(
        f"All checks passed              : "
        f"{holding_limit_result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

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

    print(
        f"Manual approval required       : "
        f"{result.manual_approval_required}"
    )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Signal file             : "
        f"{result.source_signal_file}"
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
    result: PositionStateResult,
    long_result: PositionStateResult,
    holding_limit_result: PositionStateResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True/False로 출력합니다.
    """

    source_signal_path = (
        Path(result.source_signal_file)
        if result.source_signal_file
        else None
    )

    expected_flat_action = (
        "ENTER_LONG"
        if result.signal == "BUY"
        else "NO_ACTION"
    )

    expected_long_action = (
        "EXIT_LONG"
        if result.signal == "SELL"
        else "HOLD_POSITION"
    )

    checks = {
        "Version is V9.2": (
            result.version == "V9.2"
        ),
        "Manager status is valid": (
            result.manager_status
            in VALID_MANAGER_STATUSES
        ),
        "Position state is valid": (
            result.position_state
            in VALID_POSITION_STATES
        ),
        "Action is valid": (
            result.recommended_action
            in VALID_POSITION_ACTIONS
        ),
        "Signal is valid": (
            result.signal
            in {
                "BUY",
                "HOLD",
                "SELL",
            }
        ),
        "Default position is FLAT": (
            result.position_state == "FLAT"
        ),
        "Default shares are zero": (
            result.current_position.shares == 0
        ),
        "Default action matches": (
            result.recommended_action
            == expected_flat_action
        ),
        "Signal result loaded": (
            result.signal_result_loaded
        ),
        "Position loaded": (
            result.position_loaded
        ),
        "Position valid": (
            result.position_valid
        ),
        "Signal valid": (
            result.signal_valid
        ),
        "Transition valid": (
            result.transition_valid
        ),
        "Action generated": (
            result.action_generated
        ),
        "All checks passed": (
            result.all_checks_passed
        ),
        "Long scenario valid": (
            long_result.position_state
            == "LONG"
        ),
        "Long action matches": (
            long_result.recommended_action
            == expected_long_action
        ),
        "Long checks passed": (
            long_result.all_checks_passed
        ),
        "Holding limit reached": (
            holding_limit_result
            .holding_limit_reached
        ),
        "Holding limit exits": (
            holding_limit_result
            .recommended_action
            == "EXIT_LONG"
        ),
        "Holding limit action required": (
            holding_limit_result
            .action_required
        ),
        "Holding limit checks passed": (
            holding_limit_result
            .all_checks_passed
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
        "Manual approval required": (
            result.manual_approval_required
        ),
        "Position is immutable": True,
        "Reasons exist": bool(
            result.reasons
        ),
        "Warnings exist": bool(
            result.warnings
        ),
        "Next actions exist": bool(
            result.next_actions
        ),
        "Source signal file exists": (
            source_signal_path.exists()
            if source_signal_path
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
            f"{check_name:<40}: {check_result}"
        )

    print("=" * 140)


def main() -> None:
    """
    V9.2 Position State Manager 통합 테스트입니다.

    검사 항목:

    1. V9.0 Trading Engine 실행
    2. V9.1 Signal Engine 실행
    3. 기본 FLAT 포지션 처리
    4. LONG 포지션 처리
    5. 최대 보유기간 도달 처리
    6. BUY/HOLD/SELL 전환 규칙
    7. 포지션 데이터 유효성
    8. 주문 생성 차단
    9. JSON Report 및 Latest 저장
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

        signal_result = (
            run_signal_engine_runtime_adapter(
                symbol=symbol,
                period="5y",
                interval="1d",
                trading_engine=trading_engine,
            )
        )

        (
            signal_report_path,
            signal_latest_path,
        ) = save_signal_engine_runtime_adapter(
            signal_result
        )

        if not signal_report_path.exists():
            raise RuntimeError(
                "V9.1 Signal Engine Report 파일이 없습니다."
            )

        if not signal_latest_path.exists():
            raise RuntimeError(
                "V9.1 Signal Engine Latest 파일이 없습니다."
            )

        result = run_position_state_manager(
            symbol=symbol,
            current_position=None,
            signal_result=signal_result,
        )

        (
            report_path,
            latest_path,
        ) = save_position_state_manager(
            result
        )

        print_position_state_manager(
            result
        )

        validate_result_structure(
            result
        )

        validate_current_position_is_immutable(
            result.current_position
        )

        validate_signal_matches(
            result=result,
            signal_result=signal_result,
        )

        validate_default_flat_position()

        validate_position_helper(
            result.current_position
        )

        validate_signal_helper(
            signal_result
        )

        validate_expected_action(
            result
        )

        validate_transition_result(
            result
        )

        validate_manager_status_result(
            result
        )

        validate_flat_action_rules()

        validate_long_action_rules()

        validate_holding_limit_rule()

        validate_invalid_action_rules()

        validate_execution_safety(
            result
        )

        validate_default_flat_result(
            result
        )

        long_result = (
            validate_long_position_scenario(
                signal_result
            )
        )

        holding_limit_result = (
            validate_holding_limit_scenario(
                signal_result
            )
        )

        validate_saved_files(
            result=result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_test_result(
            result=result,
            long_result=long_result,
            holding_limit_result=holding_limit_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_validation_checks(
            result=result,
            long_result=long_result,
            holding_limit_result=holding_limit_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V9.2 position state manager "
            "test completed successfully."
        )

        print(
            f"현재 Signal은 {result.signal}이고 "
            f"기본 FLAT 상태의 추천 행동은 "
            f"{result.recommended_action}입니다."
        )

        print(
            f"LONG 상태의 추천 행동은 "
            f"{long_result.recommended_action}입니다."
        )

        print(
            "최대 보유기간 도달 시 Signal과 관계없이 "
            "EXIT_LONG 검토 행동이 정상 생성되었습니다."
        )

        print(
            "포지션 상태와 추천 행동만 계산되었으며 "
            "실제 주문, 모의 주문 및 실거래 주문은 "
            "모두 차단되었습니다."
        )

        print(
            "주의: 이 테스트는 연구용 포지션 상태 판단이며 "
            "실제 계좌 조회나 증권 주문을 실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V9.2 Position State Manager "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V9.2 POSITION STATE MANAGER ERROR"
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