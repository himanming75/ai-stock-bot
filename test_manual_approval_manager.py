import json
from dataclasses import FrozenInstanceError, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from backtest.manual_approval_manager import (
    VALID_APPROVAL_REQUESTS,
    VALID_APPROVAL_STATUSES,
    ApprovalPolicy,
    ManualApprovalResult,
    calculate_expiration,
    determine_approval_decision,
    parse_datetime,
    run_manual_approval_manager,
    save_manual_approval_manager,
    validate_approval_policy,
    validate_order_ticket,
    validate_ticket_against_policy,
)
from backtest.order_ticket_builder import (
    OrderTicket,
    build_order_ticket,
    save_order_ticket,
)
from backtest.position_sizing_manager import (
    PositionSizingResult,
    run_position_sizing_manager,
    save_position_sizing_manager,
)


def print_header() -> None:
    """
    V9.6 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V9.6 "
        "MANUAL APPROVAL MANAGER TEST"
    )
    print("=" * 140)


def print_check(
    name: str,
    value: bool,
) -> None:
    """
    검증 결과를 출력합니다.
    """

    print(
        f"{name:<44}: {value}"
    )


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


def validate_policy_structure(
    policy: ApprovalPolicy,
) -> None:
    """
    ApprovalPolicy 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        policy,
        ApprovalPolicy,
    ):
        raise RuntimeError(
            "Approval Policy 형식이 올바르지 않습니다."
        )

    integer_fields = {
        "approval_expiration_minutes": (
            policy.approval_expiration_minutes
        ),
        "minimum_quantity": (
            policy.minimum_quantity
        ),
        "maximum_quantity": (
            policy.maximum_quantity
        ),
    }

    for field_name, value in integer_fields.items():
        if not isinstance(
            value,
            int,
        ):
            raise RuntimeError(
                f"{field_name}가 int 형식이 아닙니다."
            )

    numeric_fields = {
        "minimum_estimated_value": (
            policy.minimum_estimated_value
        ),
        "maximum_estimated_value": (
            policy.maximum_estimated_value
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

    boolean_fields = {
        "allow_buy": policy.allow_buy,
        "allow_sell": policy.allow_sell,
        "allow_market_order": (
            policy.allow_market_order
        ),
        "paper_only": policy.paper_only,
        "require_manual_approval": (
            policy.require_manual_approval
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

    expected_keys = {
        "approval_expiration_minutes",
        "minimum_quantity",
        "maximum_quantity",
        "minimum_estimated_value",
        "maximum_estimated_value",
        "allow_buy",
        "allow_sell",
        "allow_market_order",
        "paper_only",
        "require_manual_approval",
    }

    if set(
        policy.to_dict().keys()
    ) != expected_keys:
        raise RuntimeError(
            "ApprovalPolicy.to_dict() 구조가 "
            "예상 결과와 일치하지 않습니다."
        )


def validate_policy_is_immutable(
    policy: ApprovalPolicy,
) -> None:
    """
    ApprovalPolicy가 Frozen Dataclass인지 검사합니다.
    """

    original_value = (
        policy.approval_expiration_minutes
    )

    immutable = False

    try:
        policy.approval_expiration_minutes = 999

    except (
        FrozenInstanceError,
        AttributeError,
    ):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "ApprovalPolicy 값을 직접 변경할 수 있습니다."
        )

    if (
        policy.approval_expiration_minutes
        != original_value
    ):
        raise RuntimeError(
            "불변 ApprovalPolicy 값이 변경되었습니다."
        )


def validate_policy_helper(
    policy: ApprovalPolicy,
) -> None:
    """
    정상 ApprovalPolicy가 유효한지 검사합니다.
    """

    (
        policy_valid,
        policy_errors,
    ) = validate_approval_policy(
        policy
    )

    if not policy_valid:
        raise RuntimeError(
            "정상 ApprovalPolicy가 검사에 실패했습니다: "
            f"{policy_errors}"
        )

    if policy_errors:
        raise RuntimeError(
            "정상 ApprovalPolicy 검사에서 "
            "Error가 생성되었습니다."
        )


def validate_invalid_policies() -> None:
    """
    잘못된 ApprovalPolicy가 정상적으로 거부되는지 검사합니다.
    """

    invalid_policies = [
        ApprovalPolicy(
            approval_expiration_minutes=0,
        ),
        ApprovalPolicy(
            approval_expiration_minutes=20_000,
        ),
        ApprovalPolicy(
            minimum_quantity=0,
        ),
        ApprovalPolicy(
            minimum_quantity=100,
            maximum_quantity=10,
        ),
        ApprovalPolicy(
            minimum_estimated_value=0.0,
        ),
        ApprovalPolicy(
            minimum_estimated_value=1_000.0,
            maximum_estimated_value=100.0,
        ),
        ApprovalPolicy(
            paper_only=False,
        ),
        ApprovalPolicy(
            require_manual_approval=False,
        ),
    ]

    for policy in invalid_policies:
        (
            policy_valid,
            errors,
        ) = validate_approval_policy(
            policy
        )

        if policy_valid:
            raise RuntimeError(
                "잘못된 ApprovalPolicy가 "
                "유효한 것으로 판정되었습니다."
            )

        if not errors:
            raise RuntimeError(
                "잘못된 ApprovalPolicy 검사에서 "
                "Error 메시지가 생성되지 않았습니다."
            )


def validate_sizing_result(
    sizing_result: PositionSizingResult,
) -> None:
    """
    V9.4 Position Sizing 결과를 검사합니다.
    """

    if not isinstance(
        sizing_result,
        PositionSizingResult,
    ):
        raise RuntimeError(
            "Sizing 결과가 PositionSizingResult 형식이 아닙니다."
        )

    if sizing_result.version != "V9.4":
        raise RuntimeError(
            "Position Sizing 버전이 V9.4가 아닙니다."
        )

    if not sizing_result.all_checks_passed:
        raise RuntimeError(
            "V9.4 검사가 모두 통과되지 않았습니다."
        )

    if not sizing_result.execution_blocked:
        raise RuntimeError(
            "V9.4 Execution이 차단되지 않았습니다."
        )

    if sizing_result.order_generated:
        raise RuntimeError(
            "V9.4에서 실제 주문이 생성되었습니다."
        )

    if sizing_result.paper_order_generated:
        raise RuntimeError(
            "V9.4에서 Paper 주문이 생성되었습니다."
        )

    if sizing_result.live_order_generated:
        raise RuntimeError(
            "V9.4에서 Live 주문이 생성되었습니다."
        )


def validate_ticket(
    ticket: OrderTicket,
) -> None:
    """
    V9.5 Order Ticket을 검사합니다.
    """

    (
        ticket_valid,
        ticket_errors,
    ) = validate_order_ticket(
        ticket
    )

    if not ticket_valid:
        raise RuntimeError(
            "정상 Order Ticket이 검사에 실패했습니다: "
            f"{ticket_errors}"
        )

    if ticket_errors:
        raise RuntimeError(
            "정상 Order Ticket 검사에서 "
            "Error가 생성되었습니다."
        )


def validate_ticket_policy(
    ticket: OrderTicket,
    policy: ApprovalPolicy,
) -> None:
    """
    정상 티켓이 승인 정책을 통과하는지 검사합니다.
    """

    (
        policy_valid,
        policy_errors,
    ) = validate_ticket_against_policy(
        ticket=ticket,
        policy=policy,
    )

    if not policy_valid:
        raise RuntimeError(
            "정상 Order Ticket이 Approval Policy를 "
            "통과하지 못했습니다: "
            f"{policy_errors}"
        )

    if policy_errors:
        raise RuntimeError(
            "정상 Ticket Policy 검사에서 "
            "Error가 생성되었습니다."
        )


def validate_result_structure(
    result: ManualApprovalResult,
) -> None:
    """
    ManualApprovalResult 구조와 필수값을 검사합니다.
    """

    if not isinstance(
        result,
        ManualApprovalResult,
    ):
        raise RuntimeError(
            "결과가 ManualApprovalResult 형식이 아닙니다."
        )

    if result.version != "V9.6":
        raise RuntimeError(
            f"버전이 V9.6이 아닙니다: {result.version}"
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
        result.approval_request
        not in VALID_APPROVAL_REQUESTS
    ):
        raise RuntimeError(
            "올바르지 않은 Approval Request입니다: "
            f"{result.approval_request}"
        )

    if (
        result.approval_status
        not in VALID_APPROVAL_STATUSES
    ):
        raise RuntimeError(
            "올바르지 않은 Approval Status입니다: "
            f"{result.approval_status}"
        )

    if not result.approval_status_label:
        raise RuntimeError(
            "Approval Status Label이 비어 있습니다."
        )

    if result.ticket_version != "V9.5":
        raise RuntimeError(
            "Source Ticket Version이 V9.5가 아닙니다."
        )

    if result.ticket_side not in {
        "BUY",
        "SELL",
        "NONE",
    }:
        raise RuntimeError(
            "올바르지 않은 Ticket Side입니다."
        )

    if not isinstance(
        result.quantity,
        int,
    ):
        raise RuntimeError(
            "Quantity가 int 형식이 아닙니다."
        )

    if result.quantity < 0:
        raise RuntimeError(
            "Quantity가 음수입니다."
        )

    if result.reference_price <= 0:
        raise RuntimeError(
            "Reference Price가 0 이하입니다."
        )

    if result.estimated_value < 0:
        raise RuntimeError(
            "Estimated Value가 음수입니다."
        )

    expected_value = round(
        result.quantity
        * result.reference_price,
        2,
    )

    if abs(
        result.estimated_value
        - expected_value
    ) > 0.01:
        raise RuntimeError(
            "Estimated Value 계산이 일치하지 않습니다."
        )

    parse_datetime(
        result.created_at
    )

    parse_datetime(
        result.ticket_created_at
    )

    parse_datetime(
        result.expires_at
    )

    boolean_fields = {
        "approved": result.approved,
        "rejected": result.rejected,
        "expired": result.expired,
        "blocked": result.blocked,
        "paper_execution_allowed": (
            result.paper_execution_allowed
        ),
        "live_execution_allowed": (
            result.live_execution_allowed
        ),
        "source_loaded": result.source_loaded,
        "source_valid": result.source_valid,
        "ticket_checks_passed": (
            result.ticket_checks_passed
        ),
        "expiration_checks_passed": (
            result.expiration_checks_passed
        ),
        "policy_checks_passed": (
            result.policy_checks_passed
        ),
        "decision_generated": (
            result.decision_generated
        ),
        "all_checks_passed": (
            result.all_checks_passed
        ),
        "order_generated": result.order_generated,
        "broker_order_generated": (
            result.broker_order_generated
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

        if not value:
            raise RuntimeError(
                f"{field_name}가 비어 있습니다."
            )

    validate_policy_structure(
        result.approval_policy
    )


def validate_result_matches_ticket(
    result: ManualApprovalResult,
    ticket: OrderTicket,
) -> None:
    """
    승인 결과가 원본 Order Ticket과 일치하는지 검사합니다.
    """

    text_comparisons = {
        "symbol": (
            result.symbol,
            ticket.symbol,
        ),
        "ticket_version": (
            result.ticket_version,
            ticket.version,
        ),
        "ticket_status": (
            result.ticket_status,
            ticket.status,
        ),
        "ticket_side": (
            result.ticket_side,
            ticket.side,
        ),
        "order_type": (
            result.order_type,
            ticket.order_type,
        ),
        "time_in_force": (
            result.time_in_force,
            ticket.time_in_force,
        ),
        "ticket_created_at": (
            result.ticket_created_at,
            ticket.created_at,
        ),
    }

    for field_name, (
        actual_value,
        expected_value,
    ) in text_comparisons.items():
        if actual_value != expected_value:
            raise RuntimeError(
                f"{field_name}가 Order Ticket과 "
                "일치하지 않습니다."
            )

    if result.quantity != ticket.quantity:
        raise RuntimeError(
            "Quantity가 Order Ticket과 일치하지 않습니다."
        )

    if abs(
        result.reference_price
        - ticket.reference_price
    ) > 0.0001:
        raise RuntimeError(
            "Reference Price가 Order Ticket과 "
            "일치하지 않습니다."
        )

    if abs(
        result.estimated_value
        - ticket.estimated_value
    ) > 0.01:
        raise RuntimeError(
            "Estimated Value가 Order Ticket과 "
            "일치하지 않습니다."
        )


def validate_wait_result(
    result: ManualApprovalResult,
) -> None:
    """
    WAIT 승인 대기 상태를 검사합니다.
    """

    if result.approval_request != "WAIT":
        raise RuntimeError(
            "WAIT 결과의 Approval Request가 WAIT가 아닙니다."
        )

    if result.approval_status != "WAITING_APPROVAL":
        raise RuntimeError(
            "WAIT 결과가 WAITING_APPROVAL이 아닙니다."
        )

    if result.approved:
        raise RuntimeError(
            "WAIT 상태에서 Approved가 True입니다."
        )

    if result.rejected:
        raise RuntimeError(
            "WAIT 상태에서 Rejected가 True입니다."
        )

    if result.expired:
        raise RuntimeError(
            "WAIT 상태에서 Expired가 True입니다."
        )

    if result.blocked:
        raise RuntimeError(
            "WAIT 상태에서 Blocked가 True입니다."
        )

    if result.paper_execution_allowed:
        raise RuntimeError(
            "WAIT 상태에서 Paper Execution이 허용되었습니다."
        )

    if result.live_execution_allowed:
        raise RuntimeError(
            "WAIT 상태에서 Live Execution이 허용되었습니다."
        )

    if not result.manual_approval_required:
        raise RuntimeError(
            "WAIT 상태에서 Manual Approval Required가 "
            "False입니다."
        )


def validate_approved_result(
    result: ManualApprovalResult,
) -> None:
    """
    APPROVE_PAPER 결과를 검사합니다.
    """

    if result.approval_request != "APPROVE_PAPER":
        raise RuntimeError(
            "승인 결과의 Approval Request가 "
            "APPROVE_PAPER가 아닙니다."
        )

    if result.approval_status != "APPROVED_FOR_PAPER":
        raise RuntimeError(
            "승인 결과가 APPROVED_FOR_PAPER가 아닙니다."
        )

    if not result.approved:
        raise RuntimeError(
            "APPROVED_FOR_PAPER 상태에서 Approved가 False입니다."
        )

    if result.rejected:
        raise RuntimeError(
            "APPROVED_FOR_PAPER 상태에서 Rejected가 True입니다."
        )

    if result.expired:
        raise RuntimeError(
            "APPROVED_FOR_PAPER 상태에서 Expired가 True입니다."
        )

    if result.blocked:
        raise RuntimeError(
            "APPROVED_FOR_PAPER 상태에서 Blocked가 True입니다."
        )

    if not result.paper_execution_allowed:
        raise RuntimeError(
            "APPROVED_FOR_PAPER 상태에서 "
            "Paper Execution Allowed가 False입니다."
        )

    if result.live_execution_allowed:
        raise RuntimeError(
            "APPROVED_FOR_PAPER 상태에서 "
            "Live Execution이 허용되었습니다."
        )

    if result.approved_at is None:
        raise RuntimeError(
            "Approved At이 기록되지 않았습니다."
        )

    if result.rejected_at is not None:
        raise RuntimeError(
            "승인 상태인데 Rejected At이 기록되었습니다."
        )

    if result.manual_approval_required:
        raise RuntimeError(
            "승인 완료 상태에서 Manual Approval Required가 "
            "True입니다."
        )


def validate_rejected_result(
    result: ManualApprovalResult,
) -> None:
    """
    REJECT 결과를 검사합니다.
    """

    if result.approval_request != "REJECT":
        raise RuntimeError(
            "거절 결과의 Approval Request가 REJECT가 아닙니다."
        )

    if result.approval_status != "REJECTED":
        raise RuntimeError(
            "거절 결과가 REJECTED가 아닙니다."
        )

    if result.approved:
        raise RuntimeError(
            "REJECTED 상태에서 Approved가 True입니다."
        )

    if not result.rejected:
        raise RuntimeError(
            "REJECTED 상태에서 Rejected가 False입니다."
        )

    if result.paper_execution_allowed:
        raise RuntimeError(
            "REJECTED 상태에서 Paper Execution이 허용되었습니다."
        )

    if result.live_execution_allowed:
        raise RuntimeError(
            "REJECTED 상태에서 Live Execution이 허용되었습니다."
        )

    if result.rejected_at is None:
        raise RuntimeError(
            "Rejected At이 기록되지 않았습니다."
        )

    if result.approved_at is not None:
        raise RuntimeError(
            "거절 상태인데 Approved At이 기록되었습니다."
        )


def validate_expired_result(
    result: ManualApprovalResult,
) -> None:
    """
    만료된 Ticket 결과를 검사합니다.
    """

    if result.approval_status != "EXPIRED":
        raise RuntimeError(
            "만료 시나리오 결과가 EXPIRED가 아닙니다."
        )

    if not result.expired:
        raise RuntimeError(
            "EXPIRED 상태에서 Expired가 False입니다."
        )

    if result.approved:
        raise RuntimeError(
            "EXPIRED 상태에서 Approved가 True입니다."
        )

    if result.rejected:
        raise RuntimeError(
            "EXPIRED 상태에서 Rejected가 True입니다."
        )

    if result.paper_execution_allowed:
        raise RuntimeError(
            "EXPIRED 상태에서 Paper Execution이 허용되었습니다."
        )

    if result.live_execution_allowed:
        raise RuntimeError(
            "EXPIRED 상태에서 Live Execution이 허용되었습니다."
        )

    if result.minutes_until_expiration > 0:
        raise RuntimeError(
            "EXPIRED 상태인데 만료까지 남은 시간이 양수입니다."
        )


def validate_execution_safety(
    result: ManualApprovalResult,
) -> None:
    """
    실제 주문이나 체결이 생성되지 않았는지 검사합니다.
    """

    if result.order_generated:
        raise RuntimeError(
            "V9.6에서 실제 주문이 생성되었습니다."
        )

    if result.broker_order_generated:
        raise RuntimeError(
            "V9.6에서 Broker 주문이 생성되었습니다."
        )

    if result.paper_order_generated:
        raise RuntimeError(
            "V9.6에서 Paper 주문이 생성되었습니다."
        )

    if result.live_order_generated:
        raise RuntimeError(
            "V9.6에서 Live 주문이 생성되었습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "V9.6 Execution Blocked가 False입니다."
        )

    warning_text = " ".join(
        str(warning)
        for warning in result.warnings
    ).lower()

    if "broker" not in warning_text:
        raise RuntimeError(
            "Warnings에 Broker 차단 설명이 없습니다."
        )

    if "live" not in warning_text:
        raise RuntimeError(
            "Warnings에 Live Execution 차단 설명이 없습니다."
        )


def validate_expiration_helpers(
    ticket: OrderTicket,
    policy: ApprovalPolicy,
) -> None:
    """
    Expiration Helper 함수들을 검사합니다.
    """

    created_at = parse_datetime(
        ticket.created_at
    )

    current_time = (
        created_at
        + timedelta(
            minutes=10,
        )
    )

    (
        expires_at,
        minutes_remaining,
        expired,
    ) = calculate_expiration(
        ticket_created_at=ticket.created_at,
        expiration_minutes=(
            policy.approval_expiration_minutes
        ),
        current_time=current_time,
    )

    expected_expiration = (
        created_at
        + timedelta(
            minutes=policy.approval_expiration_minutes
        )
    )

    if expires_at != expected_expiration:
        raise RuntimeError(
            "Expiration Time 계산이 일치하지 않습니다."
        )

    expected_remaining = (
        policy.approval_expiration_minutes
        - 10
    )

    if abs(
        minutes_remaining
        - expected_remaining
    ) > 0.001:
        raise RuntimeError(
            "Minutes Until Expiration 계산이 "
            "일치하지 않습니다."
        )

    if expired:
        raise RuntimeError(
            "유효한 티켓이 Expired로 판정되었습니다."
        )

    expired_time = (
        expected_expiration
        + timedelta(
            seconds=1,
        )
    )

    (
        _,
        expired_minutes,
        expired_status,
    ) = calculate_expiration(
        ticket_created_at=ticket.created_at,
        expiration_minutes=(
            policy.approval_expiration_minutes
        ),
        current_time=expired_time,
    )

    if not expired_status:
        raise RuntimeError(
            "만료된 티켓이 Expired로 판정되지 않았습니다."
        )

    if expired_minutes >= 0:
        raise RuntimeError(
            "만료된 티켓의 남은 시간이 음수가 아닙니다."
        )


def validate_decision_rules() -> None:
    """
    WAIT, APPROVE_PAPER, REJECT, EXPIRED, BLOCKED 규칙을 검사합니다.
    """

    test_cases = [
        {
            "request": "WAIT",
            "ticket_valid": True,
            "policy_valid": True,
            "expiration_valid": True,
            "expired": False,
            "expected_status": "WAITING_APPROVAL",
            "approved": False,
            "rejected": False,
            "expired_result": False,
            "blocked": False,
        },
        {
            "request": "APPROVE_PAPER",
            "ticket_valid": True,
            "policy_valid": True,
            "expiration_valid": True,
            "expired": False,
            "expected_status": "APPROVED_FOR_PAPER",
            "approved": True,
            "rejected": False,
            "expired_result": False,
            "blocked": False,
        },
        {
            "request": "REJECT",
            "ticket_valid": True,
            "policy_valid": True,
            "expiration_valid": True,
            "expired": False,
            "expected_status": "REJECTED",
            "approved": False,
            "rejected": True,
            "expired_result": False,
            "blocked": False,
        },
        {
            "request": "APPROVE_PAPER",
            "ticket_valid": True,
            "policy_valid": True,
            "expiration_valid": True,
            "expired": True,
            "expected_status": "EXPIRED",
            "approved": False,
            "rejected": False,
            "expired_result": True,
            "blocked": False,
        },
        {
            "request": "APPROVE_PAPER",
            "ticket_valid": False,
            "policy_valid": True,
            "expiration_valid": True,
            "expired": False,
            "expected_status": "BLOCKED",
            "approved": False,
            "rejected": False,
            "expired_result": False,
            "blocked": True,
        },
    ]

    for test_case in test_cases:
        (
            status,
            label,
            approved,
            rejected,
            expired_result,
            blocked,
            reasons,
        ) = determine_approval_decision(
            approval_request=(
                test_case["request"]
            ),
            ticket_valid=(
                test_case["ticket_valid"]
            ),
            policy_valid=(
                test_case["policy_valid"]
            ),
            expiration_valid=(
                test_case["expiration_valid"]
            ),
            expired=(
                test_case["expired"]
            ),
        )

        if status != test_case["expected_status"]:
            raise RuntimeError(
                "Approval Decision 규칙이 일치하지 않습니다. "
                f"Expected={test_case['expected_status']}, "
                f"Actual={status}"
            )

        if approved != test_case["approved"]:
            raise RuntimeError(
                "Approval Decision의 Approved 값이 "
                "일치하지 않습니다."
            )

        if rejected != test_case["rejected"]:
            raise RuntimeError(
                "Approval Decision의 Rejected 값이 "
                "일치하지 않습니다."
            )

        if expired_result != test_case["expired_result"]:
            raise RuntimeError(
                "Approval Decision의 Expired 값이 "
                "일치하지 않습니다."
            )

        if blocked != test_case["blocked"]:
            raise RuntimeError(
                "Approval Decision의 Blocked 값이 "
                "일치하지 않습니다."
            )

        if not label:
            raise RuntimeError(
                "Approval Status Label이 비어 있습니다."
            )

        if not reasons:
            raise RuntimeError(
                "Approval Decision Reasons가 비어 있습니다."
            )


def validate_invalid_request(
    ticket: OrderTicket,
) -> None:
    """
    잘못된 Approval Request가 거부되는지 검사합니다.
    """

    error_raised = False

    try:
        run_manual_approval_manager(
            symbol=ticket.symbol,
            ticket=ticket,
            approval_request="LIVE_APPROVE",
        )

    except ValueError:
        error_raised = True

    if not error_raised:
        raise RuntimeError(
            "잘못된 Approval Request가 거부되지 않았습니다."
        )


def validate_expired_scenario(
    ticket: OrderTicket,
    policy: ApprovalPolicy,
) -> ManualApprovalResult:
    """
    만료된 Order Ticket 승인 시나리오를 실행합니다.
    """

    ticket_created_at = parse_datetime(
        ticket.created_at
    )

    expired_time = (
        ticket_created_at
        + timedelta(
            minutes=(
                policy.approval_expiration_minutes
                + 1
            )
        )
    )

    result = run_manual_approval_manager(
        symbol=ticket.symbol,
        ticket=ticket,
        approval_request="APPROVE_PAPER",
        approval_actor="TEST_USER",
        approval_note="Expired scenario test",
        approval_policy=policy,
        current_time=expired_time,
    )

    validate_expired_result(
        result
    )

    validate_execution_safety(
        result
    )

    return result


def validate_blocked_policy_scenario(
    ticket: OrderTicket,
) -> ManualApprovalResult:
    """
    Ticket 수량이 승인 정책을 초과할 때 BLOCKED인지 검사합니다.
    """

    restrictive_policy = ApprovalPolicy(
        maximum_quantity=max(
            1,
            ticket.quantity - 1,
        ),
        maximum_estimated_value=max(
            25.0,
            ticket.estimated_value - 1.0,
        ),
    )

    result = run_manual_approval_manager(
        symbol=ticket.symbol,
        ticket=ticket,
        approval_request="APPROVE_PAPER",
        approval_actor="TEST_USER",
        approval_note="Restrictive policy test",
        approval_policy=restrictive_policy,
        current_time=parse_datetime(
            ticket.created_at
        ),
    )

    if ticket.quantity > 1:
        if result.approval_status != "BLOCKED":
            raise RuntimeError(
                "제한 정책 시나리오가 BLOCKED가 아닙니다."
            )

        if not result.blocked:
            raise RuntimeError(
                "BLOCKED 시나리오에서 Blocked가 False입니다."
            )

        if result.paper_execution_allowed:
            raise RuntimeError(
                "BLOCKED 시나리오에서 "
                "Paper Execution이 허용되었습니다."
            )

    validate_execution_safety(
        result
    )

    return result


def validate_saved_files(
    result: ManualApprovalResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    저장된 V9.6 JSON 파일을 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            f"Report 파일이 없습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            f"Latest 파일이 없습니다: {latest_path}"
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "Report와 Latest JSON 내용이 일치하지 않습니다."
        )

    expected_payload = result.to_dict()

    if report_payload != expected_payload:
        raise RuntimeError(
            "저장된 JSON 내용이 실행 결과와 일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "source_order_ticket_file",
        "approval_status",
        "approval_status_label",
        "approval_request",
        "approved",
        "rejected",
        "expired",
        "blocked",
        "ticket_version",
        "ticket_status",
        "ticket_side",
        "quantity",
        "reference_price",
        "estimated_value",
        "order_type",
        "time_in_force",
        "ticket_created_at",
        "expires_at",
        "minutes_until_expiration",
        "approval_actor",
        "approval_note",
        "approved_at",
        "rejected_at",
        "paper_execution_allowed",
        "live_execution_allowed",
        "source_loaded",
        "source_valid",
        "ticket_checks_passed",
        "expiration_checks_passed",
        "policy_checks_passed",
        "decision_generated",
        "all_checks_passed",
        "order_generated",
        "broker_order_generated",
        "paper_order_generated",
        "live_order_generated",
        "execution_blocked",
        "manual_approval_required",
        "approval_policy",
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
            "저장된 V9.6 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
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
    wait_result: ManualApprovalResult,
    approved_result: ManualApprovalResult,
    rejected_result: ManualApprovalResult,
    expired_result: ManualApprovalResult,
    blocked_result: ManualApprovalResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V9.6 MANUAL APPROVAL MANAGER "
        "TEST RESULT"
    )
    print("=" * 140)

    print("WAIT SCENARIO")
    print("-" * 140)

    print(
        f"Approval status                : "
        f"{wait_result.approval_status}"
    )

    print(
        f"Paper execution allowed        : "
        f"{wait_result.paper_execution_allowed}"
    )

    print(
        f"Manual approval required       : "
        f"{wait_result.manual_approval_required}"
    )

    print()
    print("APPROVED SCENARIO")
    print("-" * 140)

    print(
        f"Approval status                : "
        f"{approved_result.approval_status}"
    )

    print(
        f"Approved                       : "
        f"{approved_result.approved}"
    )

    print(
        f"Paper execution allowed        : "
        f"{approved_result.paper_execution_allowed}"
    )

    print(
        f"Live execution allowed         : "
        f"{approved_result.live_execution_allowed}"
    )

    print(
        f"Approved at                    : "
        f"{approved_result.approved_at}"
    )

    print()
    print("REJECTED SCENARIO")
    print("-" * 140)

    print(
        f"Approval status                : "
        f"{rejected_result.approval_status}"
    )

    print(
        f"Rejected                       : "
        f"{rejected_result.rejected}"
    )

    print(
        f"Paper execution allowed        : "
        f"{rejected_result.paper_execution_allowed}"
    )

    print()
    print("EXPIRED SCENARIO")
    print("-" * 140)

    print(
        f"Approval status                : "
        f"{expired_result.approval_status}"
    )

    print(
        f"Expired                        : "
        f"{expired_result.expired}"
    )

    print(
        f"Minutes until expiration       : "
        f"{expired_result.minutes_until_expiration:.2f}"
    )

    print()
    print("BLOCKED POLICY SCENARIO")
    print("-" * 140)

    print(
        f"Approval status                : "
        f"{blocked_result.approval_status}"
    )

    print(
        f"Blocked                        : "
        f"{blocked_result.blocked}"
    )

    print(
        f"Paper execution allowed        : "
        f"{blocked_result.paper_execution_allowed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Order generated                : "
        f"{approved_result.order_generated}"
    )

    print(
        f"Broker order generated         : "
        f"{approved_result.broker_order_generated}"
    )

    print(
        f"Paper order generated          : "
        f"{approved_result.paper_order_generated}"
    )

    print(
        f"Live order generated           : "
        f"{approved_result.live_order_generated}"
    )

    print(
        f"Execution blocked              : "
        f"{approved_result.execution_blocked}"
    )

    print()
    print("FILES")
    print("-" * 140)

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
    wait_result: ManualApprovalResult,
    approved_result: ManualApprovalResult,
    rejected_result: ManualApprovalResult,
    expired_result: ManualApprovalResult,
    blocked_result: ManualApprovalResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True/False로 출력합니다.
    """

    checks = {
        "Version is V9.6": (
            approved_result.version == "V9.6"
        ),
        "WAIT status is valid": (
            wait_result.approval_status
            == "WAITING_APPROVAL"
        ),
        "WAIT requires approval": (
            wait_result.manual_approval_required
        ),
        "WAIT blocks paper execution": (
            not wait_result.paper_execution_allowed
        ),
        "APPROVE status is valid": (
            approved_result.approval_status
            == "APPROVED_FOR_PAPER"
        ),
        "APPROVE flag is true": (
            approved_result.approved
        ),
        "Paper execution allowed": (
            approved_result.paper_execution_allowed
        ),
        "Live execution remains blocked": (
            not approved_result.live_execution_allowed
        ),
        "REJECT status is valid": (
            rejected_result.approval_status
            == "REJECTED"
        ),
        "REJECT flag is true": (
            rejected_result.rejected
        ),
        "Rejected ticket blocks paper": (
            not rejected_result.paper_execution_allowed
        ),
        "EXPIRED status is valid": (
            expired_result.approval_status
            == "EXPIRED"
        ),
        "Expired flag is true": (
            expired_result.expired
        ),
        "Expired ticket blocks paper": (
            not expired_result.paper_execution_allowed
        ),
        "Blocked scenario is valid": (
            blocked_result.approval_status
            in {
                "BLOCKED",
                "APPROVED_FOR_PAPER",
            }
        ),
        "Source loaded": (
            approved_result.source_loaded
        ),
        "Source valid": (
            approved_result.source_valid
        ),
        "Ticket checks passed": (
            approved_result.ticket_checks_passed
        ),
        "Expiration checks passed": (
            approved_result.expiration_checks_passed
        ),
        "Policy checks passed": (
            approved_result.policy_checks_passed
        ),
        "Decision generated": (
            approved_result.decision_generated
        ),
        "All checks passed": (
            approved_result.all_checks_passed
        ),
        "Order not generated": (
            not approved_result.order_generated
        ),
        "Broker order not generated": (
            not approved_result.broker_order_generated
        ),
        "Paper order not generated": (
            not approved_result.paper_order_generated
        ),
        "Live order not generated": (
            not approved_result.live_order_generated
        ),
        "Execution remains blocked": (
            approved_result.execution_blocked
        ),
        "Policy is immutable": True,
        "Reasons exist": bool(
            approved_result.reasons
        ),
        "Warnings exist": bool(
            approved_result.warnings
        ),
        "Next actions exist": bool(
            approved_result.next_actions
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

    for name, value in checks.items():
        print_check(
            name,
            value,
        )

    print("=" * 140)

    failed_checks = [
        name
        for name, value in checks.items()
        if not value
    ]

    if failed_checks:
        raise RuntimeError(
            "다음 검증 항목이 실패했습니다: "
            f"{failed_checks}"
        )


def main() -> None:
    """
    V9.6 Manual Approval Manager 통합 테스트입니다.

    검사 시나리오:

    1. WAIT
    2. APPROVE_PAPER
    3. REJECT
    4. EXPIRED
    5. 제한 정책 BLOCKED
    6. 주문 및 체결 생성 차단
    7. JSON 저장
    """

    symbol = "AAPL"
    account_cash = 10_000.0

    print_header()

    try:
        sizing_result = run_position_sizing_manager(
            symbol=symbol,
            account_cash=account_cash,
        )

        (
            sizing_report_path,
            sizing_latest_path,
        ) = save_position_sizing_manager(
            sizing_result
        )

        if not sizing_report_path.exists():
            raise RuntimeError(
                "V9.4 Position Sizing Report 파일이 없습니다."
            )

        if not sizing_latest_path.exists():
            raise RuntimeError(
                "V9.4 Position Sizing Latest 파일이 없습니다."
            )

        validate_sizing_result(
            sizing_result
        )

        ticket = build_order_ticket(
            sizing_result
        )

        (
            ticket_report_path,
            ticket_latest_path,
        ) = save_order_ticket(
            ticket
        )

        if not ticket_report_path.exists():
            raise RuntimeError(
                "V9.5 Order Ticket Report 파일이 없습니다."
            )

        if not ticket_latest_path.exists():
            raise RuntimeError(
                "V9.5 Order Ticket Latest 파일이 없습니다."
            )

        validate_ticket(
            ticket
        )

        policy = ApprovalPolicy()

        validate_policy_structure(
            policy
        )

        validate_policy_is_immutable(
            policy
        )

        validate_policy_helper(
            policy
        )

        validate_invalid_policies()

        validate_ticket_policy(
            ticket=ticket,
            policy=policy,
        )

        validate_expiration_helpers(
            ticket=ticket,
            policy=policy,
        )

        validate_decision_rules()

        validate_invalid_request(
            ticket
        )

        scenario_time = parse_datetime(
            ticket.created_at
        )

        wait_result = run_manual_approval_manager(
            symbol=symbol,
            ticket=ticket,
            approval_request="WAIT",
            approval_actor="TEST_USER",
            approval_note="Waiting scenario",
            approval_policy=policy,
            current_time=scenario_time,
        )

        validate_result_structure(
            wait_result
        )

        validate_result_matches_ticket(
            result=wait_result,
            ticket=ticket,
        )

        validate_wait_result(
            wait_result
        )

        validate_execution_safety(
            wait_result
        )

        approved_result = run_manual_approval_manager(
            symbol=symbol,
            ticket=ticket,
            approval_request="APPROVE_PAPER",
            approval_actor="TEST_USER",
            approval_note=(
                "Paper trading approval integration test"
            ),
            approval_policy=policy,
            current_time=scenario_time,
        )

        validate_result_structure(
            approved_result
        )

        validate_result_matches_ticket(
            result=approved_result,
            ticket=ticket,
        )

        validate_approved_result(
            approved_result
        )

        validate_execution_safety(
            approved_result
        )

        rejected_result = run_manual_approval_manager(
            symbol=symbol,
            ticket=ticket,
            approval_request="REJECT",
            approval_actor="TEST_USER",
            approval_note="Rejected scenario",
            approval_policy=policy,
            current_time=scenario_time,
        )

        validate_result_structure(
            rejected_result
        )

        validate_result_matches_ticket(
            result=rejected_result,
            ticket=ticket,
        )

        validate_rejected_result(
            rejected_result
        )

        validate_execution_safety(
            rejected_result
        )

        expired_result = validate_expired_scenario(
            ticket=ticket,
            policy=policy,
        )

        blocked_result = (
            validate_blocked_policy_scenario(
                ticket=ticket,
            )
        )

        (
            report_path,
            latest_path,
        ) = save_manual_approval_manager(
            approved_result
        )

        validate_saved_files(
            result=approved_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_test_result(
            wait_result=wait_result,
            approved_result=approved_result,
            rejected_result=rejected_result,
            expired_result=expired_result,
            blocked_result=blocked_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_validation_checks(
            wait_result=wait_result,
            approved_result=approved_result,
            rejected_result=rejected_result,
            expired_result=expired_result,
            blocked_result=blocked_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V9.6 manual approval manager "
            "test completed successfully."
        )

        print(
            "WAIT, APPROVE_PAPER, REJECT, EXPIRED 및 "
            "BLOCKED 승인 규칙이 정상 검증되었습니다."
        )

        print(
            f"승인 테스트 결과는 "
            f"{approved_result.approval_status}이며 "
            f"Paper Execution Allowed는 "
            f"{approved_result.paper_execution_allowed}입니다."
        )

        print(
            "단, Paper 주문이나 가상 체결은 아직 "
            "생성되지 않았습니다."
        )

        print(
            "Broker 주문과 Live 주문은 계속 차단되었습니다."
        )

        print(
            "주의: 이 결과는 연구용 Paper Trading 승인 기록이며 "
            "실제 증권 주문 승인이 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V9.6 Manual Approval Manager "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V9.6 MANUAL APPROVAL MANAGER ERROR"
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

        raise


if __name__ == "__main__":
    main()