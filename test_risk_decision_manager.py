import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

from backtest.position_state_manager import (
    CurrentPosition,
    PositionStateResult,
    run_position_state_manager,
    save_position_state_manager,
)
from backtest.risk_decision_manager import (
    VALID_POSITION_ACTIONS,
    VALID_RISK_DECISIONS,
    VALID_RISK_LEVELS,
    VALID_RISK_STATUSES,
    RiskDecisionResult,
    RiskLimits,
    calculate_position_metrics,
    calculate_risk_score,
    clamp,
    determine_risk_decision,
    determine_risk_level,
    determine_risk_status,
    is_valid_number,
    print_risk_decision_manager,
    run_risk_decision_manager,
    save_risk_decision_manager,
    validate_current_position,
    validate_position_state_result,
    validate_risk_limits,
    validate_risk_parameters,
)
from backtest.signal_engine_runtime_adapter import (
    run_signal_engine_runtime_adapter,
    save_signal_engine_runtime_adapter,
)
from backtest.trading_engine_integration import (
    run_trading_engine_integration,
    save_trading_engine_integration,
)


def print_test_header() -> None:
    """
    V9.3 Risk Decision Manager 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V9.3 "
        "RISK DECISION MANAGER TEST"
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


def validate_risk_limits_structure(
    limits: RiskLimits,
) -> None:
    """
    RiskLimits 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        limits,
        RiskLimits,
    ):
        raise RuntimeError(
            "risk_limits가 RiskLimits 형식이 아닙니다."
        )

    float_fields = {
        "maximum_position_percent": (
            limits.maximum_position_percent
        ),
        "reduced_position_percent": (
            limits.reduced_position_percent
        ),
        "maximum_stop_atr": (
            limits.maximum_stop_atr
        ),
        "maximum_target_atr": (
            limits.maximum_target_atr
        ),
        "minimum_entry_score": (
            limits.minimum_entry_score
        ),
        "minimum_score_margin": (
            limits.minimum_score_margin
        ),
        "maximum_price_distance_percent": (
            limits.maximum_price_distance_percent
        ),
        "manual_review_position_percent": (
            limits.manual_review_position_percent
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
        limits.maximum_holding_days,
        int,
    ):
        raise RuntimeError(
            "maximum_holding_days가 int 형식이 아닙니다."
        )

    required_keys = {
        "maximum_position_percent",
        "reduced_position_percent",
        "maximum_stop_atr",
        "maximum_target_atr",
        "maximum_holding_days",
        "minimum_entry_score",
        "minimum_score_margin",
        "maximum_price_distance_percent",
        "manual_review_position_percent",
    }

    payload = limits.to_dict()

    if set(payload.keys()) != required_keys:
        raise RuntimeError(
            "RiskLimits.to_dict() 구조가 "
            "예상 결과와 일치하지 않습니다."
        )


def validate_risk_limits_are_immutable(
    limits: RiskLimits,
) -> None:
    """
    RiskLimits가 frozen Dataclass인지 검사합니다.
    """

    original_value = (
        limits.maximum_position_percent
    )

    immutable = False

    try:
        limits.maximum_position_percent = 99.0

    except (
        FrozenInstanceError,
        AttributeError,
    ):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "RiskLimits 값을 직접 변경할 수 있습니다."
        )

    if (
        limits.maximum_position_percent
        != original_value
    ):
        raise RuntimeError(
            "불변 RiskLimits 값이 변경되었습니다."
        )


def validate_result_structure(
    result: RiskDecisionResult,
) -> None:
    """
    V9.3 결과 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        result,
        RiskDecisionResult,
    ):
        raise RuntimeError(
            "결과가 RiskDecisionResult 형식이 아닙니다."
        )

    if result.version != "V9.3":
        raise RuntimeError(
            f"버전이 V9.3이 아닙니다: {result.version}"
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

    if result.risk_status not in VALID_RISK_STATUSES:
        raise RuntimeError(
            "올바르지 않은 Risk Status입니다: "
            f"{result.risk_status}"
        )

    if result.risk_decision not in VALID_RISK_DECISIONS:
        raise RuntimeError(
            "올바르지 않은 Risk Decision입니다: "
            f"{result.risk_decision}"
        )

    if result.risk_level not in VALID_RISK_LEVELS:
        raise RuntimeError(
            "올바르지 않은 Risk Level입니다: "
            f"{result.risk_level}"
        )

    if result.position_action not in VALID_POSITION_ACTIONS:
        raise RuntimeError(
            "올바르지 않은 Position Action입니다: "
            f"{result.position_action}"
        )

    if result.position_state not in {
        "FLAT",
        "LONG",
    }:
        raise RuntimeError(
            "올바르지 않은 Position State입니다: "
            f"{result.position_state}"
        )

    if result.signal not in {
        "BUY",
        "HOLD",
        "SELL",
    }:
        raise RuntimeError(
            f"올바르지 않은 Signal입니다: {result.signal}"
        )

    if not result.risk_decision_label:
        raise RuntimeError(
            "Risk Decision Label이 비어 있습니다."
        )

    validate_risk_limits_structure(
        result.risk_limits
    )

    numeric_fields = {
        "risk_score": result.risk_score,
        "current_score": result.current_score,
        "entry_score": result.entry_score,
        "exit_score": result.exit_score,
        "score_margin": result.score_margin,
        "latest_close": result.latest_close,
        "stop_atr_multiple": result.stop_atr_multiple,
        "target_atr_multiple": result.target_atr_multiple,
        "requested_position_percent": (
            result.requested_position_percent
        ),
        "approved_position_percent": (
            result.approved_position_percent
        ),
        "position_reduction_percent": (
            result.position_reduction_percent
        ),
        "average_price": result.average_price,
        "estimated_position_value": (
            result.estimated_position_value
        ),
    }

    for field_name, value in numeric_fields.items():
        if not is_valid_number(value):
            raise RuntimeError(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    if (
        result.unrealized_return_percent
        is not None
        and not is_valid_number(
            result.unrealized_return_percent
        )
    ):
        raise RuntimeError(
            "Unrealized Return Percent가 "
            "유효한 숫자가 아닙니다."
        )

    integer_fields = {
        "maximum_holding_days": (
            result.maximum_holding_days
        ),
        "holding_days": result.holding_days,
        "current_shares": result.current_shares,
    }

    for field_name, value in integer_fields.items():
        if not isinstance(
            value,
            int,
        ):
            raise RuntimeError(
                f"{field_name}가 int 형식이 아닙니다."
            )

    boolean_fields = {
        "action_required": result.action_required,
        "holding_limit_reached": (
            result.holding_limit_reached
        ),
        "source_loaded": result.source_loaded,
        "source_valid": result.source_valid,
        "action_valid": result.action_valid,
        "parameter_checks_passed": (
            result.parameter_checks_passed
        ),
        "position_checks_passed": (
            result.position_checks_passed
        ),
        "score_checks_passed": (
            result.score_checks_passed
        ),
        "risk_checks_passed": (
            result.risk_checks_passed
        ),
        "decision_generated": (
            result.decision_generated
        ),
        "all_checks_passed": (
            result.all_checks_passed
        ),
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


def validate_source_matches(
    result: RiskDecisionResult,
    position_result: PositionStateResult,
) -> None:
    """
    V9.3 결과가 V9.2 Position State 결과와 일치하는지 검사합니다.
    """

    if result.symbol != position_result.symbol:
        raise RuntimeError(
            "V9.3 Symbol이 V9.2 결과와 일치하지 않습니다."
        )

    comparisons = {
        "position_action": (
            result.position_action,
            position_result.recommended_action,
        ),
        "position_state": (
            result.position_state,
            position_result.position_state,
        ),
        "signal": (
            result.signal,
            position_result.signal,
        ),
        "latest_date": (
            result.latest_date,
            position_result.latest_date,
        ),
        "strategy_source": (
            result.strategy_source,
            position_result.strategy_source,
        ),
        "strategy_status": (
            result.strategy_status,
            position_result.strategy_status,
        ),
        "strategy_name": (
            result.strategy_name,
            position_result.strategy_name,
        ),
        "strategy_type": (
            result.strategy_type,
            position_result.strategy_type,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in comparisons.items():
        if actual_value != expected_value:
            raise RuntimeError(
                f"{field_name}가 V9.2 결과와 "
                "일치하지 않습니다."
            )

    numeric_comparisons = {
        "current_score": (
            result.current_score,
            position_result.current_score,
        ),
        "entry_score": (
            result.entry_score,
            position_result.entry_score,
        ),
        "exit_score": (
            result.exit_score,
            position_result.exit_score,
        ),
        "latest_close": (
            result.latest_close,
            position_result.latest_close,
        ),
        "requested_position_percent": (
            result.requested_position_percent,
            position_result.position_percent,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in numeric_comparisons.items():
        if abs(
            float(actual_value)
            - float(expected_value)
        ) > 0.0001:
            raise RuntimeError(
                f"{field_name}가 V9.2 결과와 "
                "일치하지 않습니다."
            )

    if (
        result.maximum_holding_days
        != position_result.maximum_holding_days
    ):
        raise RuntimeError(
            "Maximum Holding Days가 V9.2 결과와 "
            "일치하지 않습니다."
        )

    if (
        result.holding_days
        != position_result.current_position.holding_days
    ):
        raise RuntimeError(
            "Holding Days가 V9.2 결과와 일치하지 않습니다."
        )

    if (
        result.current_shares
        != position_result.current_position.shares
    ):
        raise RuntimeError(
            "Current Shares가 V9.2 결과와 일치하지 않습니다."
        )

    if abs(
        result.average_price
        - position_result.current_position.average_price
    ) > 0.0001:
        raise RuntimeError(
            "Average Price가 V9.2 결과와 일치하지 않습니다."
        )


def validate_limit_helper(
    limits: RiskLimits,
) -> None:
    """
    validate_risk_limits Helper를 검사합니다.
    """

    (
        limits_valid,
        limit_errors,
    ) = validate_risk_limits(
        limits
    )

    if not limits_valid:
        raise RuntimeError(
            "정상 RiskLimits가 검사에 실패했습니다: "
            f"{limit_errors}"
        )

    if limit_errors:
        raise RuntimeError(
            "정상 RiskLimits 검사에서 Error가 생성되었습니다."
        )


def validate_invalid_limits() -> None:
    """
    잘못된 RiskLimits가 정상적으로 거부되는지 검사합니다.
    """

    invalid_limits_list = [
        RiskLimits(
            maximum_position_percent=0.0,
        ),
        RiskLimits(
            maximum_position_percent=20.0,
            reduced_position_percent=25.0,
        ),
        RiskLimits(
            maximum_stop_atr=0.1,
        ),
        RiskLimits(
            maximum_target_atr=30.0,
        ),
        RiskLimits(
            maximum_holding_days=0,
        ),
        RiskLimits(
            minimum_entry_score=120.0,
        ),
        RiskLimits(
            minimum_score_margin=-1.0,
        ),
        RiskLimits(
            manual_review_position_percent=25.0,
            maximum_position_percent=20.0,
        ),
    ]

    for limits in invalid_limits_list:
        (
            limits_valid,
            errors,
        ) = validate_risk_limits(
            limits
        )

        if limits_valid:
            raise RuntimeError(
                "잘못된 RiskLimits가 유효한 것으로 "
                "판정되었습니다."
            )

        if not errors:
            raise RuntimeError(
                "잘못된 RiskLimits 검사에서 "
                "Error 메시지가 생성되지 않았습니다."
            )


def validate_source_helper(
    position_result: PositionStateResult,
) -> None:
    """
    validate_position_state_result Helper를 검사합니다.
    """

    (
        source_valid,
        source_errors,
    ) = validate_position_state_result(
        position_result
    )

    if not source_valid:
        raise RuntimeError(
            "정상 V9.2 결과가 검사에 실패했습니다: "
            f"{source_errors}"
        )

    if source_errors:
        raise RuntimeError(
            "정상 V9.2 결과 검사에서 Error가 생성되었습니다."
        )


def validate_parameter_helper(
    position_result: PositionStateResult,
    limits: RiskLimits,
) -> None:
    """
    validate_risk_parameters Helper를 검사합니다.
    """

    (
        parameters_valid,
        parameter_errors,
    ) = validate_risk_parameters(
        position_result=position_result,
        limits=limits,
    )

    if not parameters_valid:
        raise RuntimeError(
            "정상 위험 파라미터가 검사에 실패했습니다: "
            f"{parameter_errors}"
        )

    if parameter_errors:
        raise RuntimeError(
            "정상 위험 파라미터 검사에서 "
            "Error가 생성되었습니다."
        )


def validate_position_helper(
    position: CurrentPosition,
) -> None:
    """
    validate_current_position Helper를 검사합니다.
    """

    (
        position_valid,
        position_errors,
    ) = validate_current_position(
        position
    )

    if not position_valid:
        raise RuntimeError(
            "정상 CurrentPosition이 검사에 실패했습니다: "
            f"{position_errors}"
        )

    if position_errors:
        raise RuntimeError(
            "정상 CurrentPosition 검사에서 "
            "Error가 생성되었습니다."
        )


def validate_clamp_helper() -> None:
    """
    clamp 함수의 범위 제한 기능을 검사합니다.
    """

    test_cases = [
        {
            "value": -10.0,
            "minimum": 0.0,
            "maximum": 100.0,
            "expected": 0.0,
        },
        {
            "value": 50.0,
            "minimum": 0.0,
            "maximum": 100.0,
            "expected": 50.0,
        },
        {
            "value": 150.0,
            "minimum": 0.0,
            "maximum": 100.0,
            "expected": 100.0,
        },
    ]

    for test_case in test_cases:
        actual_value = clamp(
            value=test_case["value"],
            minimum=test_case["minimum"],
            maximum=test_case["maximum"],
        )

        if actual_value != test_case["expected"]:
            raise RuntimeError(
                "clamp 결과가 예상값과 일치하지 않습니다."
            )


def validate_risk_level_rules() -> None:
    """
    Risk Score별 Risk Level 규칙을 검사합니다.
    """

    test_cases = [
        (0.0, "LOW"),
        (29.99, "LOW"),
        (30.0, "MEDIUM"),
        (59.99, "MEDIUM"),
        (60.0, "HIGH"),
        (79.99, "HIGH"),
        (80.0, "CRITICAL"),
        (100.0, "CRITICAL"),
    ]

    for risk_score, expected_level in test_cases:
        actual_level = determine_risk_level(
            risk_score
        )

        if actual_level != expected_level:
            raise RuntimeError(
                "Risk Level 규칙이 일치하지 않습니다. "
                f"Score={risk_score}, "
                f"Expected={expected_level}, "
                f"Actual={actual_level}"
            )


def validate_position_metrics_rules() -> None:
    """
    FLAT 및 LONG 포지션 가치 계산을 검사합니다.
    """

    flat_position = CurrentPosition()

    (
        flat_value,
        flat_return,
    ) = calculate_position_metrics(
        position=flat_position,
        latest_close=200.0,
    )

    if flat_value != 0.0:
        raise RuntimeError(
            "FLAT Position Value가 0이 아닙니다."
        )

    if flat_return is not None:
        raise RuntimeError(
            "FLAT Unrealized Return이 None이 아닙니다."
        )

    long_position = CurrentPosition(
        state="LONG",
        shares=10,
        average_price=100.0,
        entry_date="2026-01-01",
        holding_days=5,
    )

    (
        long_value,
        long_return,
    ) = calculate_position_metrics(
        position=long_position,
        latest_close=120.0,
    )

    if abs(
        long_value
        - 1200.0
    ) > 0.0001:
        raise RuntimeError(
            "LONG Position Value 계산이 일치하지 않습니다."
        )

    if long_return is None:
        raise RuntimeError(
            "LONG Unrealized Return이 None입니다."
        )

    if abs(
        long_return
        - 20.0
    ) > 0.0001:
        raise RuntimeError(
            "LONG Unrealized Return 계산이 일치하지 않습니다."
        )


def validate_risk_score_result(
    result: RiskDecisionResult,
    position_result: PositionStateResult,
) -> None:
    """
    calculate_risk_score 결과와 실제 결과를 비교합니다.
    """

    (
        expected_score,
        expected_reasons,
    ) = calculate_risk_score(
        position_result=position_result,
        limits=result.risk_limits,
    )

    if abs(
        result.risk_score
        - expected_score
    ) > 0.0001:
        raise RuntimeError(
            "Risk Score가 예상 결과와 일치하지 않습니다."
        )

    for reason in expected_reasons:
        if reason not in result.reasons:
            raise RuntimeError(
                "Risk Score Reason이 결과에 없습니다: "
                f"{reason}"
            )

    expected_level = determine_risk_level(
        result.risk_score
    )

    if result.risk_level != expected_level:
        raise RuntimeError(
            "Risk Level이 Risk Score와 일치하지 않습니다."
        )


def validate_decision_result(
    result: RiskDecisionResult,
) -> None:
    """
    determine_risk_decision 결과와 실제 결과를 비교합니다.
    """

    (
        expected_decision,
        expected_label,
        expected_approved_percent,
        expected_manual_review,
        expected_reasons,
    ) = determine_risk_decision(
        position_action=result.position_action,
        risk_score=result.risk_score,
        requested_position_percent=(
            result.requested_position_percent
        ),
        limits=result.risk_limits,
        source_valid=result.source_valid,
        parameter_checks_passed=(
            result.parameter_checks_passed
        ),
        position_checks_passed=(
            result.position_checks_passed
        ),
    )

    if result.risk_decision != expected_decision:
        raise RuntimeError(
            "Risk Decision이 예상 결과와 일치하지 않습니다. "
            f"Expected={expected_decision}, "
            f"Actual={result.risk_decision}"
        )

    if result.risk_decision_label != expected_label:
        raise RuntimeError(
            "Risk Decision Label이 예상 결과와 "
            "일치하지 않습니다."
        )

    if abs(
        result.approved_position_percent
        - expected_approved_percent
    ) > 0.0001:
        raise RuntimeError(
            "Approved Position Percent가 예상 결과와 "
            "일치하지 않습니다."
        )

    if (
        result.manual_approval_required
        != expected_manual_review
    ):
        raise RuntimeError(
            "Manual Approval Required가 예상 결과와 "
            "일치하지 않습니다."
        )

    for reason in expected_reasons:
        if reason not in result.reasons:
            raise RuntimeError(
                "Decision Reason이 결과에 없습니다: "
                f"{reason}"
            )


def validate_status_result(
    result: RiskDecisionResult,
) -> None:
    """
    Risk Status 계산 결과를 검사합니다.
    """

    expected_status = determine_risk_status(
        risk_decision=result.risk_decision,
        decision_generated=result.decision_generated,
        all_core_checks_passed=(
            result.source_valid
            and result.action_valid
            and result.parameter_checks_passed
            and result.position_checks_passed
            and result.score_checks_passed
            and result.risk_checks_passed
        ),
    )

    if result.risk_status != expected_status:
        raise RuntimeError(
            "Risk Status가 예상 결과와 일치하지 않습니다. "
            f"Expected={expected_status}, "
            f"Actual={result.risk_status}"
        )


def validate_position_percent_math(
    result: RiskDecisionResult,
) -> None:
    """
    승인 및 축소 포지션 비율 계산을 검사합니다.
    """

    expected_reduction = max(
        0.0,
        result.requested_position_percent
        - result.approved_position_percent,
    )

    if abs(
        result.position_reduction_percent
        - expected_reduction
    ) > 0.0001:
        raise RuntimeError(
            "Position Reduction Percent 계산이 "
            "일치하지 않습니다."
        )

    if result.approved_position_percent < 0:
        raise RuntimeError(
            "Approved Position Percent가 음수입니다."
        )

    if (
        result.approved_position_percent
        > result.requested_position_percent
    ):
        raise RuntimeError(
            "Approved Position Percent가 요청값보다 큽니다."
        )

    if (
        result.approved_position_percent
        > result.risk_limits.maximum_position_percent
    ):
        raise RuntimeError(
            "Approved Position Percent가 최대 위험 한도를 "
            "초과했습니다."
        )


def validate_decision_rules() -> None:
    """
    ALLOW, REDUCE_SIZE, REVIEW_REQUIRED, BLOCK,
    NO_ACTION 규칙을 직접 검사합니다.
    """

    limits = RiskLimits()

    test_cases = [
        {
            "action": "ENTER_LONG",
            "risk_score": 10.0,
            "requested": 15.0,
            "expected": "ALLOW",
            "approved": 15.0,
        },
        {
            "action": "ENTER_LONG",
            "risk_score": 40.0,
            "requested": 15.0,
            "expected": "REDUCE_SIZE",
            "approved": 10.0,
        },
        {
            "action": "ENTER_LONG",
            "risk_score": 65.0,
            "requested": 15.0,
            "expected": "REVIEW_REQUIRED",
            "approved": 0.0,
        },
        {
            "action": "ENTER_LONG",
            "risk_score": 85.0,
            "requested": 15.0,
            "expected": "BLOCK",
            "approved": 0.0,
        },
        {
            "action": "NO_ACTION",
            "risk_score": 0.0,
            "requested": 15.0,
            "expected": "NO_ACTION",
            "approved": 0.0,
        },
        {
            "action": "HOLD_POSITION",
            "risk_score": 10.0,
            "requested": 15.0,
            "expected": "ALLOW",
            "approved": 15.0,
        },
        {
            "action": "EXIT_LONG",
            "risk_score": 10.0,
            "requested": 15.0,
            "expected": "ALLOW",
            "approved": 15.0,
        },
        {
            "action": "EXIT_LONG",
            "risk_score": 85.0,
            "requested": 15.0,
            "expected": "REVIEW_REQUIRED",
            "approved": 15.0,
        },
        {
            "action": "BLOCKED",
            "risk_score": 100.0,
            "requested": 15.0,
            "expected": "BLOCK",
            "approved": 0.0,
        },
    ]

    for test_case in test_cases:
        (
            decision,
            label,
            approved_percent,
            _,
            reasons,
        ) = determine_risk_decision(
            position_action=test_case["action"],
            risk_score=test_case["risk_score"],
            requested_position_percent=(
                test_case["requested"]
            ),
            limits=limits,
            source_valid=True,
            parameter_checks_passed=True,
            position_checks_passed=True,
        )

        if decision != test_case["expected"]:
            raise RuntimeError(
                "Risk Decision 규칙이 일치하지 않습니다. "
                f"Action={test_case['action']}, "
                f"Score={test_case['risk_score']}, "
                f"Expected={test_case['expected']}, "
                f"Actual={decision}"
            )

        if abs(
            approved_percent
            - test_case["approved"]
        ) > 0.0001:
            raise RuntimeError(
                "Risk Decision Approved Percent가 "
                "예상 결과와 일치하지 않습니다."
            )

        if not label:
            raise RuntimeError(
                "Risk Decision Label이 비어 있습니다."
            )

        if not reasons:
            raise RuntimeError(
                "Risk Decision Reasons가 비어 있습니다."
            )


def validate_failed_check_rule() -> None:
    """
    필수 검사 실패 시 Risk Decision이 BLOCK인지 검사합니다.
    """

    (
        decision,
        _,
        approved_percent,
        manual_review,
        reasons,
    ) = determine_risk_decision(
        position_action="ENTER_LONG",
        risk_score=0.0,
        requested_position_percent=15.0,
        limits=RiskLimits(),
        source_valid=False,
        parameter_checks_passed=True,
        position_checks_passed=True,
    )

    if decision != "BLOCK":
        raise RuntimeError(
            "Source 검사 실패 시 BLOCK이 생성되지 않았습니다."
        )

    if approved_percent != 0.0:
        raise RuntimeError(
            "검사 실패 BLOCK 상태에서 Approved Percent가 "
            "0이 아닙니다."
        )

    if not manual_review:
        raise RuntimeError(
            "검사 실패 BLOCK 상태에서 Manual Review가 "
            "False입니다."
        )

    if not reasons:
        raise RuntimeError(
            "검사 실패 BLOCK 상태 Reasons가 비어 있습니다."
        )


def validate_execution_safety(
    result: RiskDecisionResult,
) -> None:
    """
    V9.3에서 주문이 생성되지 않았는지 검사합니다.
    """

    if result.order_generated:
        raise RuntimeError(
            "V9.3에서 실제 Order가 생성되었습니다."
        )

    if result.paper_order_generated:
        raise RuntimeError(
            "V9.3에서 Paper Order가 생성되었습니다."
        )

    if result.live_order_generated:
        raise RuntimeError(
            "V9.3에서 Live Order가 생성되었습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "V9.3에서 Execution Blocked가 False입니다."
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


def create_long_position_result(
    symbol: str,
    holding_days: int,
) -> PositionStateResult:
    """
    LONG 포지션 V9.2 결과를 생성합니다.
    """

    long_position = CurrentPosition(
        state="LONG",
        shares=10,
        average_price=300.0,
        entry_date="2026-07-01",
        holding_days=holding_days,
    )

    return run_position_state_manager(
        symbol=symbol,
        current_position=long_position,
        period="5y",
        interval="1d",
    )


def validate_long_scenario(
    symbol: str,
) -> RiskDecisionResult:
    """
    LONG 포지션 유지 또는 종료 시나리오를 검사합니다.
    """

    position_result = create_long_position_result(
        symbol=symbol,
        holding_days=5,
    )

    result = run_risk_decision_manager(
        symbol=symbol,
        position_result=position_result,
    )

    if result.position_state != "LONG":
        raise RuntimeError(
            "LONG Risk 시나리오의 Position State가 "
            "LONG이 아닙니다."
        )

    expected_action = (
        "EXIT_LONG"
        if result.signal == "SELL"
        else "HOLD_POSITION"
    )

    if result.position_action != expected_action:
        raise RuntimeError(
            "LONG Risk 시나리오 Position Action이 "
            "예상 결과와 일치하지 않습니다."
        )

    if result.risk_decision not in {
        "ALLOW",
        "REVIEW_REQUIRED",
    }:
        raise RuntimeError(
            "LONG Risk 시나리오 Decision이 "
            "허용 범위에 없습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "LONG Risk 시나리오 All Checks Passed가 "
            "False입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_holding_limit_scenario(
    symbol: str,
) -> RiskDecisionResult:
    """
    최대 보유기간 도달 위험 시나리오를 검사합니다.
    """

    position_result = create_long_position_result(
        symbol=symbol,
        holding_days=20,
    )

    if not position_result.holding_limit_reached:
        raise RuntimeError(
            "V9.2 Holding Limit Reached가 False입니다."
        )

    result = run_risk_decision_manager(
        symbol=symbol,
        position_result=position_result,
    )

    if result.position_action != "EXIT_LONG":
        raise RuntimeError(
            "최대 보유기간 Risk 시나리오에서 "
            "EXIT_LONG이 전달되지 않았습니다."
        )

    if not result.holding_limit_reached:
        raise RuntimeError(
            "V9.3 Holding Limit Reached가 False입니다."
        )

    if result.risk_decision not in {
        "ALLOW",
        "REVIEW_REQUIRED",
    }:
        raise RuntimeError(
            "최대 보유기간 Risk Decision이 "
            "허용 범위에 없습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "최대 보유기간 Risk 시나리오 검사가 "
            "통과되지 않았습니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_reduced_size_rule(
    position_result: PositionStateResult,
) -> None:
    """
    높은 요청 포지션 비율에서 REDUCE_SIZE가 발생하는지 검사합니다.
    """

    high_position_result = replace(
        position_result,
        position_percent=20.0,
    )

    limits = RiskLimits(
        maximum_position_percent=20.0,
        reduced_position_percent=10.0,
        manual_review_position_percent=15.0,
    )

    result = run_risk_decision_manager(
        symbol=high_position_result.symbol,
        position_result=high_position_result,
        risk_limits=limits,
    )

    if high_position_result.recommended_action == "ENTER_LONG":
        if result.risk_decision != "REDUCE_SIZE":
            raise RuntimeError(
                "높은 Position Percent의 ENTER_LONG에서 "
                "REDUCE_SIZE가 생성되지 않았습니다."
            )

        if result.approved_position_percent != 10.0:
            raise RuntimeError(
                "REDUCE_SIZE 승인 비율이 10%가 아닙니다."
            )

        if result.position_reduction_percent != 10.0:
            raise RuntimeError(
                "REDUCE_SIZE 축소 비율이 10%p가 아닙니다."
            )


def validate_saved_files(
    result: RiskDecisionResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.3 JSON 저장 결과를 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            f"V9.3 Report 파일이 없습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            f"V9.3 Latest 파일이 없습니다: {latest_path}"
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "V9.3 Report와 Latest 파일 내용이 "
            "일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_position_state_file",
        "risk_status",
        "risk_decision",
        "risk_decision_label",
        "risk_level",
        "risk_score",
        "position_action",
        "position_state",
        "signal",
        "action_required",
        "current_score",
        "entry_score",
        "exit_score",
        "score_margin",
        "latest_close",
        "latest_date",
        "stop_atr_multiple",
        "target_atr_multiple",
        "maximum_holding_days",
        "holding_days",
        "holding_limit_reached",
        "requested_position_percent",
        "approved_position_percent",
        "position_reduction_percent",
        "current_shares",
        "average_price",
        "estimated_position_value",
        "unrealized_return_percent",
        "strategy_source",
        "strategy_status",
        "strategy_name",
        "strategy_type",
        "risk_limits",
        "source_loaded",
        "source_valid",
        "action_valid",
        "parameter_checks_passed",
        "position_checks_passed",
        "score_checks_passed",
        "risk_checks_passed",
        "decision_generated",
        "all_checks_passed",
        "order_generated",
        "paper_order_generated",
        "live_order_generated",
        "execution_blocked",
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
            "저장된 V9.3 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    text_checks = {
        "version": result.version,
        "symbol": result.symbol,
        "risk_status": result.risk_status,
        "risk_decision": result.risk_decision,
        "risk_decision_label": (
            result.risk_decision_label
        ),
        "risk_level": result.risk_level,
        "position_action": (
            result.position_action
        ),
        "position_state": (
            result.position_state
        ),
        "signal": result.signal,
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
        "risk_score": result.risk_score,
        "current_score": result.current_score,
        "entry_score": result.entry_score,
        "exit_score": result.exit_score,
        "score_margin": result.score_margin,
        "latest_close": result.latest_close,
        "stop_atr_multiple": (
            result.stop_atr_multiple
        ),
        "target_atr_multiple": (
            result.target_atr_multiple
        ),
        "requested_position_percent": (
            result.requested_position_percent
        ),
        "approved_position_percent": (
            result.approved_position_percent
        ),
        "position_reduction_percent": (
            result.position_reduction_percent
        ),
        "average_price": result.average_price,
        "estimated_position_value": (
            result.estimated_position_value
        ),
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

    integer_checks = {
        "maximum_holding_days": (
            result.maximum_holding_days
        ),
        "holding_days": result.holding_days,
        "current_shares": result.current_shares,
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
        "source_loaded": result.source_loaded,
        "source_valid": result.source_valid,
        "action_valid": result.action_valid,
        "parameter_checks_passed": (
            result.parameter_checks_passed
        ),
        "position_checks_passed": (
            result.position_checks_passed
        ),
        "score_checks_passed": (
            result.score_checks_passed
        ),
        "risk_checks_passed": (
            result.risk_checks_passed
        ),
        "decision_generated": (
            result.decision_generated
        ),
        "all_checks_passed": (
            result.all_checks_passed
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

    saved_limits = report_payload.get(
        "risk_limits"
    )

    if not isinstance(
        saved_limits,
        dict,
    ):
        raise RuntimeError(
            "저장된 Risk Limits가 Dictionary가 아닙니다."
        )

    if saved_limits != result.risk_limits.to_dict():
        raise RuntimeError(
            "저장된 Risk Limits가 실행 결과와 "
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
    result: RiskDecisionResult,
    long_result: RiskDecisionResult,
    holding_limit_result: RiskDecisionResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.3 최종 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V9.3 RISK DECISION MANAGER "
        "TEST RESULT"
    )
    print("=" * 140)

    print(
        f"Symbol                         : "
        f"{result.symbol}"
    )

    print(
        f"Risk status                    : "
        f"{result.risk_status}"
    )

    print(
        f"Risk decision                  : "
        f"{result.risk_decision}"
    )

    print(
        f"Risk level                     : "
        f"{result.risk_level}"
    )

    print(
        f"Risk score                     : "
        f"{result.risk_score:.2f}/100"
    )

    print()
    print("DEFAULT POSITION SCENARIO")
    print("-" * 140)

    print(
        f"Position state                 : "
        f"{result.position_state}"
    )

    print(
        f"Signal                         : "
        f"{result.signal}"
    )

    print(
        f"Position action                : "
        f"{result.position_action}"
    )

    print(
        f"Requested position             : "
        f"{result.requested_position_percent:.2f}%"
    )

    print(
        f"Approved position              : "
        f"{result.approved_position_percent:.2f}%"
    )

    print(
        f"Position reduction             : "
        f"{result.position_reduction_percent:.2f}%p"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("LONG POSITION SCENARIO")
    print("-" * 140)

    print(
        f"Position action                : "
        f"{long_result.position_action}"
    )

    print(
        f"Risk decision                  : "
        f"{long_result.risk_decision}"
    )

    print(
        f"Position value                 : "
        f"${long_result.estimated_position_value:,.2f}"
    )

    if long_result.unrealized_return_percent is None:
        long_return_text = "N/A"

    else:
        long_return_text = (
            f"{long_result.unrealized_return_percent:+.2f}%"
        )

    print(
        f"Unrealized return              : "
        f"{long_return_text}"
    )

    print(
        f"All checks passed              : "
        f"{long_result.all_checks_passed}"
    )

    print()
    print("HOLDING LIMIT SCENARIO")
    print("-" * 140)

    print(
        f"Holding limit reached          : "
        f"{holding_limit_result.holding_limit_reached}"
    )

    print(
        f"Position action                : "
        f"{holding_limit_result.position_action}"
    )

    print(
        f"Risk decision                  : "
        f"{holding_limit_result.risk_decision}"
    )

    print(
        f"Risk score                     : "
        f"{holding_limit_result.risk_score:.2f}/100"
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
        f"Source Position State file     : "
        f"{result.source_position_state_file}"
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
    result: RiskDecisionResult,
    long_result: RiskDecisionResult,
    holding_limit_result: RiskDecisionResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True/False로 출력합니다.
    """

    source_path = (
        Path(result.source_position_state_file)
        if result.source_position_state_file
        else None
    )

    checks = {
        "Version is V9.3": (
            result.version == "V9.3"
        ),
        "Risk status is valid": (
            result.risk_status
            in VALID_RISK_STATUSES
        ),
        "Risk decision is valid": (
            result.risk_decision
            in VALID_RISK_DECISIONS
        ),
        "Risk level is valid": (
            result.risk_level
            in VALID_RISK_LEVELS
        ),
        "Position action is valid": (
            result.position_action
            in VALID_POSITION_ACTIONS
        ),
        "Risk score is valid": (
            0.0
            <= result.risk_score
            <= 100.0
        ),
        "Source loaded": (
            result.source_loaded
        ),
        "Source valid": (
            result.source_valid
        ),
        "Action valid": (
            result.action_valid
        ),
        "Parameter checks passed": (
            result.parameter_checks_passed
        ),
        "Position checks passed": (
            result.position_checks_passed
        ),
        "Score checks passed": (
            result.score_checks_passed
        ),
        "Risk checks passed": (
            result.risk_checks_passed
        ),
        "Decision generated": (
            result.decision_generated
        ),
        "All checks passed": (
            result.all_checks_passed
        ),
        "Approved percent is valid": (
            0.0
            <= result.approved_position_percent
            <= result.requested_position_percent
        ),
        "Reduction calculation valid": (
            abs(
                result.position_reduction_percent
                - max(
                    0.0,
                    result.requested_position_percent
                    - result.approved_position_percent,
                )
            )
            <= 0.0001
        ),
        "Long scenario passed": (
            long_result.all_checks_passed
        ),
        "Long scenario state valid": (
            long_result.position_state == "LONG"
        ),
        "Holding limit reached": (
            holding_limit_result
            .holding_limit_reached
        ),
        "Holding limit action exits": (
            holding_limit_result
            .position_action
            == "EXIT_LONG"
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
        "Risk limits immutable": True,
        "Reasons exist": bool(
            result.reasons
        ),
        "Warnings exist": bool(
            result.warnings
        ),
        "Next actions exist": bool(
            result.next_actions
        ),
        "Source position file exists": (
            source_path.exists()
            if source_path
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
            f"{check_name:<42}: {check_result}"
        )

    print("=" * 140)


def main() -> None:
    """
    V9.3 Risk Decision Manager 통합 테스트입니다.

    검사 항목:

    1. V9.0 Trading Engine 실행
    2. V9.1 Signal Engine 실행
    3. V9.2 Position State Manager 실행
    4. V9.3 Risk Decision 생성
    5. Risk Score 및 Risk Level 검사
    6. ALLOW, REDUCE_SIZE, REVIEW_REQUIRED, BLOCK 규칙
    7. LONG 포지션 위험 검사
    8. 최대 보유기간 위험 검사
    9. 주문 생성 차단
    10. JSON Report 및 Latest 저장
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

        position_result = (
            run_position_state_manager(
                symbol=symbol,
                current_position=None,
                signal_result=signal_result,
            )
        )

        (
            position_report_path,
            position_latest_path,
        ) = save_position_state_manager(
            position_result
        )

        if not position_report_path.exists():
            raise RuntimeError(
                "V9.2 Position State Report 파일이 없습니다."
            )

        if not position_latest_path.exists():
            raise RuntimeError(
                "V9.2 Position State Latest 파일이 없습니다."
            )

        limits = RiskLimits()

        result = run_risk_decision_manager(
            symbol=symbol,
            position_result=position_result,
            risk_limits=limits,
        )

        (
            report_path,
            latest_path,
        ) = save_risk_decision_manager(
            result
        )

        print_risk_decision_manager(
            result
        )

        validate_result_structure(
            result
        )

        validate_risk_limits_are_immutable(
            result.risk_limits
        )

        validate_source_matches(
            result=result,
            position_result=position_result,
        )

        validate_limit_helper(
            limits
        )

        validate_invalid_limits()

        validate_source_helper(
            position_result
        )

        validate_parameter_helper(
            position_result=position_result,
            limits=limits,
        )

        validate_position_helper(
            position_result.current_position
        )

        validate_clamp_helper()

        validate_risk_level_rules()

        validate_position_metrics_rules()

        validate_risk_score_result(
            result=result,
            position_result=position_result,
        )

        validate_decision_result(
            result
        )

        validate_status_result(
            result
        )

        validate_position_percent_math(
            result
        )

        validate_decision_rules()

        validate_failed_check_rule()

        validate_execution_safety(
            result
        )

        validate_reduced_size_rule(
            position_result
        )

        long_result = validate_long_scenario(
            symbol
        )

        holding_limit_result = (
            validate_holding_limit_scenario(
                symbol
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
            "V9.3 risk decision manager "
            "test completed successfully."
        )

        print(
            f"현재 Position Action은 "
            f"{result.position_action}이고 "
            f"Risk Decision은 "
            f"{result.risk_decision}입니다."
        )

        print(
            f"Risk Score는 "
            f"{result.risk_score:.2f}/100이고 "
            f"Risk Level은 {result.risk_level}입니다."
        )

        print(
            f"요청 포지션 비율 "
            f"{result.requested_position_percent:.2f}% 중 "
            f"{result.approved_position_percent:.2f}%가 "
            "위험 판단상 승인되었습니다."
        )

        print(
            "ALLOW, REDUCE_SIZE, REVIEW_REQUIRED, "
            "BLOCK 및 NO_ACTION 규칙이 정상 검증되었습니다."
        )

        print(
            "실제 주문, 모의 주문 및 실거래 주문은 "
            "모두 생성되지 않았고 계속 차단되었습니다."
        )

        print(
            "주의: 이 테스트는 연구용 위험 판단이며 "
            "실제 계좌의 잔고, 포지션 또는 증권 주문을 "
            "조회하거나 실행하지 않습니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V9.3 Risk Decision Manager "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V9.3 RISK DECISION MANAGER ERROR"
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