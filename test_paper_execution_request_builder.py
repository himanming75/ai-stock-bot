import json
from dataclasses import FrozenInstanceError
from datetime import timedelta
from pathlib import Path
from typing import Any

from backtest.manual_approval_manager import (
    ApprovalPolicy,
    ManualApprovalResult,
    parse_datetime,
    run_manual_approval_manager,
    save_manual_approval_manager,
)
from backtest.order_ticket_builder import (
    OrderTicket,
    build_order_ticket,
    save_order_ticket,
)
from backtest.paper_execution_request_builder import (
    VALID_ORDER_TYPES,
    VALID_REQUEST_ACTIONS,
    VALID_REQUEST_STATUSES,
    VALID_SIDES,
    VALID_TIME_IN_FORCE,
    PaperExecutionPolicy,
    PaperExecutionRequestResult,
    create_idempotency_key,
    determine_request_decision,
    run_paper_execution_request_builder,
    save_paper_execution_request,
    validate_approval_for_request,
    validate_manual_approval_result,
    validate_paper_execution_policy,
    validate_request_against_policy,
)
from backtest.position_sizing_manager import (
    PositionSizingResult,
    run_position_sizing_manager,
    save_position_sizing_manager,
)


def print_header() -> None:
    """
    V9.7 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V9.7 "
        "PAPER EXECUTION REQUEST BUILDER TEST"
    )
    print("=" * 140)


def print_check(
    name: str,
    value: bool,
) -> None:
    """
    검증 결과를 True 또는 False로 출력합니다.
    """

    print(
        f"{name:<48}: {value}"
    )


def load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽어서 Dictionary로 반환합니다.
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


def validate_position_sizing_result(
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
            f"Position Sizing 버전이 V9.4가 아닙니다: "
            f"{sizing_result.version}"
        )

    if not sizing_result.source_loaded:
        raise RuntimeError(
            "V9.4 Source Loaded가 False입니다."
        )

    if not sizing_result.source_valid:
        raise RuntimeError(
            "V9.4 Source Valid가 False입니다."
        )

    if not sizing_result.all_checks_passed:
        raise RuntimeError(
            "V9.4 검사가 모두 통과되지 않았습니다."
        )

    if sizing_result.proposed_shares <= 0:
        raise RuntimeError(
            "V9.4 Proposed Shares가 0 이하입니다."
        )

    if sizing_result.proposed_position_value <= 0:
        raise RuntimeError(
            "V9.4 Proposed Position Value가 0 이하입니다."
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


def validate_order_ticket(
    ticket: OrderTicket,
    sizing_result: PositionSizingResult,
) -> None:
    """
    V9.5 Order Ticket을 검사합니다.
    """

    if not isinstance(
        ticket,
        OrderTicket,
    ):
        raise RuntimeError(
            "Order Ticket 형식이 올바르지 않습니다."
        )

    if ticket.version != "V9.5":
        raise RuntimeError(
            f"Order Ticket 버전이 V9.5가 아닙니다: "
            f"{ticket.version}"
        )

    if ticket.symbol != sizing_result.symbol:
        raise RuntimeError(
            "Order Ticket Symbol이 Position Sizing 결과와 "
            "일치하지 않습니다."
        )

    if ticket.side not in VALID_SIDES:
        raise RuntimeError(
            f"올바르지 않은 Ticket Side입니다: {ticket.side}"
        )

    if ticket.quantity != sizing_result.proposed_shares:
        raise RuntimeError(
            "Order Ticket Quantity가 Position Sizing 결과와 "
            "일치하지 않습니다."
        )

    if ticket.quantity <= 0:
        raise RuntimeError(
            "Order Ticket Quantity가 0 이하입니다."
        )

    if ticket.reference_price <= 0:
        raise RuntimeError(
            "Order Ticket Reference Price가 0 이하입니다."
        )

    expected_value = round(
        ticket.quantity
        * ticket.reference_price,
        2,
    )

    if abs(
        ticket.estimated_value
        - expected_value
    ) > 0.01:
        raise RuntimeError(
            "Order Ticket Estimated Value 계산이 "
            "일치하지 않습니다."
        )

    if ticket.order_type not in VALID_ORDER_TYPES:
        raise RuntimeError(
            "Order Ticket Order Type이 올바르지 않습니다."
        )

    if ticket.time_in_force not in VALID_TIME_IN_FORCE:
        raise RuntimeError(
            "Order Ticket Time In Force가 올바르지 않습니다."
        )

    if ticket.status != "WAITING_MANUAL_APPROVAL":
        raise RuntimeError(
            "Order Ticket Status가 "
            "WAITING_MANUAL_APPROVAL이 아닙니다."
        )

    if not ticket.execution_blocked:
        raise RuntimeError(
            "Order Ticket Execution이 차단되지 않았습니다."
        )

    if ticket.broker_order_created:
        raise RuntimeError(
            "Order Ticket 단계에서 Broker Order가 생성되었습니다."
        )

    if ticket.paper_order_created:
        raise RuntimeError(
            "Order Ticket 단계에서 Paper Order가 생성되었습니다."
        )

    if ticket.live_order_created:
        raise RuntimeError(
            "Order Ticket 단계에서 Live Order가 생성되었습니다."
        )


def validate_policy_structure(
    policy: PaperExecutionPolicy,
) -> None:
    """
    PaperExecutionPolicy 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        policy,
        PaperExecutionPolicy,
    ):
        raise RuntimeError(
            "Paper Execution Policy 형식이 올바르지 않습니다."
        )

    integer_fields = {
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
        "minimum_order_value": (
            policy.minimum_order_value
        ),
        "maximum_order_value": (
            policy.maximum_order_value
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
        "allow_limit_order": (
            policy.allow_limit_order
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
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
        "minimum_quantity",
        "maximum_quantity",
        "minimum_order_value",
        "maximum_order_value",
        "allow_buy",
        "allow_sell",
        "allow_market_order",
        "allow_limit_order",
        "paper_only",
        "live_execution_disabled",
        "require_manual_approval",
    }

    actual_keys = set(
        policy.to_dict().keys()
    )

    if actual_keys != expected_keys:
        raise RuntimeError(
            "PaperExecutionPolicy.to_dict()의 키가 "
            "예상 구조와 일치하지 않습니다."
        )


def validate_policy_is_immutable(
    policy: PaperExecutionPolicy,
) -> None:
    """
    PaperExecutionPolicy가 Frozen Dataclass인지 검사합니다.
    """

    original_value = (
        policy.maximum_quantity
    )

    immutable = False

    try:
        policy.maximum_quantity = 999

    except (
        FrozenInstanceError,
        AttributeError,
    ):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "PaperExecutionPolicy 값을 직접 변경할 수 있습니다."
        )

    if policy.maximum_quantity != original_value:
        raise RuntimeError(
            "불변 Policy 값이 변경되었습니다."
        )


def validate_normal_policy(
    policy: PaperExecutionPolicy,
) -> None:
    """
    기본 정책이 정상적으로 통과하는지 검사합니다.
    """

    (
        policy_valid,
        policy_errors,
    ) = validate_paper_execution_policy(
        policy
    )

    if not policy_valid:
        raise RuntimeError(
            "정상 Paper Execution Policy가 "
            "검사에 실패했습니다: "
            f"{policy_errors}"
        )

    if policy_errors:
        raise RuntimeError(
            "정상 Policy 검사에서 오류 메시지가 생성되었습니다."
        )


def validate_invalid_policies() -> None:
    """
    잘못된 정책이 정상적으로 거부되는지 검사합니다.
    """

    invalid_policies = [
        PaperExecutionPolicy(
            minimum_quantity=0,
        ),
        PaperExecutionPolicy(
            minimum_quantity=100,
            maximum_quantity=10,
        ),
        PaperExecutionPolicy(
            minimum_order_value=0.0,
        ),
        PaperExecutionPolicy(
            minimum_order_value=1_000.0,
            maximum_order_value=100.0,
        ),
        PaperExecutionPolicy(
            paper_only=False,
        ),
        PaperExecutionPolicy(
            live_execution_disabled=False,
        ),
        PaperExecutionPolicy(
            require_manual_approval=False,
        ),
    ]

    for policy in invalid_policies:
        (
            policy_valid,
            errors,
        ) = validate_paper_execution_policy(
            policy
        )

        if policy_valid:
            raise RuntimeError(
                "잘못된 Paper Execution Policy가 "
                "유효한 것으로 판정되었습니다."
            )

        if not errors:
            raise RuntimeError(
                "잘못된 Policy 검사에서 오류 메시지가 "
                "생성되지 않았습니다."
            )


def validate_manual_approval_source(
    approval_result: ManualApprovalResult,
) -> None:
    """
    V9.6 Manual Approval 결과의 기본 구조를 검사합니다.
    """

    (
        source_valid,
        source_errors,
    ) = validate_manual_approval_result(
        approval_result
    )

    if not source_valid:
        raise RuntimeError(
            "정상 Manual Approval 결과가 "
            "Source 검사에 실패했습니다: "
            f"{source_errors}"
        )

    if source_errors:
        raise RuntimeError(
            "정상 Manual Approval Source 검사에서 "
            "오류 메시지가 생성되었습니다."
        )


def validate_approved_manual_result(
    approval_result: ManualApprovalResult,
) -> None:
    """
    APPROVED_FOR_PAPER 승인 결과를 검사합니다.
    """

    if approval_result.version != "V9.6":
        raise RuntimeError(
            "Manual Approval 버전이 V9.6이 아닙니다."
        )

    if (
        approval_result.approval_status
        != "APPROVED_FOR_PAPER"
    ):
        raise RuntimeError(
            "Approval Status가 APPROVED_FOR_PAPER가 아닙니다."
        )

    if not approval_result.approved:
        raise RuntimeError(
            "승인 결과에서 Approved가 False입니다."
        )

    if approval_result.rejected:
        raise RuntimeError(
            "승인 결과에서 Rejected가 True입니다."
        )

    if approval_result.expired:
        raise RuntimeError(
            "승인 결과가 Expired 상태입니다."
        )

    if approval_result.blocked:
        raise RuntimeError(
            "승인 결과가 Blocked 상태입니다."
        )

    if not approval_result.paper_execution_allowed:
        raise RuntimeError(
            "Paper Execution Allowed가 False입니다."
        )

    if approval_result.live_execution_allowed:
        raise RuntimeError(
            "Live Execution Allowed가 True입니다."
        )

    if approval_result.approved_at is None:
        raise RuntimeError(
            "Approved At이 기록되지 않았습니다."
        )

    (
        approval_valid,
        approval_errors,
    ) = validate_approval_for_request(
        approval_result
    )

    if not approval_valid:
        raise RuntimeError(
            "승인된 Manual Approval 결과가 "
            "Paper Request 승인 검사에 실패했습니다: "
            f"{approval_errors}"
        )

    if approval_errors:
        raise RuntimeError(
            "승인된 결과 검사에서 오류 메시지가 생성되었습니다."
        )


def validate_approved_result_against_policy(
    approval_result: ManualApprovalResult,
    policy: PaperExecutionPolicy,
) -> None:
    """
    승인된 주문이 Paper Execution Policy에 맞는지 검사합니다.
    """

    (
        policy_valid,
        policy_errors,
    ) = validate_request_against_policy(
        approval_result=approval_result,
        policy=policy,
    )

    if not policy_valid:
        raise RuntimeError(
            "승인된 주문이 Paper Execution Policy를 "
            "통과하지 못했습니다: "
            f"{policy_errors}"
        )

    if policy_errors:
        raise RuntimeError(
            "정상 Request Policy 검사에서 오류 메시지가 "
            "생성되었습니다."
        )


def validate_result_structure(
    result: PaperExecutionRequestResult,
) -> None:
    """
    V9.7 결과의 구조와 필수값을 검사합니다.
    """

    if not isinstance(
        result,
        PaperExecutionRequestResult,
    ):
        raise RuntimeError(
            "결과가 PaperExecutionRequestResult "
            "형식이 아닙니다."
        )

    if result.version != "V9.7":
        raise RuntimeError(
            f"버전이 V9.7이 아닙니다: {result.version}"
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

    if not result.request_id:
        raise RuntimeError(
            "Request ID가 비어 있습니다."
        )

    if not result.idempotency_key:
        raise RuntimeError(
            "Idempotency Key가 비어 있습니다."
        )

    if result.request_status not in VALID_REQUEST_STATUSES:
        raise RuntimeError(
            "올바르지 않은 Request Status입니다: "
            f"{result.request_status}"
        )

    if result.request_action not in VALID_REQUEST_ACTIONS:
        raise RuntimeError(
            "올바르지 않은 Request Action입니다: "
            f"{result.request_action}"
        )

    if not result.request_status_label:
        raise RuntimeError(
            "Request Status Label이 비어 있습니다."
        )

    if not result.request_action_label:
        raise RuntimeError(
            "Request Action Label이 비어 있습니다."
        )

    if result.side not in VALID_SIDES:
        raise RuntimeError(
            f"올바르지 않은 Side입니다: {result.side}"
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

    if result.order_type not in VALID_ORDER_TYPES:
        raise RuntimeError(
            "올바르지 않은 Order Type입니다."
        )

    if result.time_in_force not in VALID_TIME_IN_FORCE:
        raise RuntimeError(
            "올바르지 않은 Time In Force입니다."
        )

    if result.reference_price <= 0:
        raise RuntimeError(
            "Reference Price가 0 이하입니다."
        )

    if result.estimated_order_value < 0:
        raise RuntimeError(
            "Estimated Order Value가 음수입니다."
        )

    expected_order_value = round(
        result.quantity
        * result.reference_price,
        2,
    )

    if abs(
        result.estimated_order_value
        - expected_order_value
    ) > 0.01:
        raise RuntimeError(
            "Estimated Order Value 계산이 일치하지 않습니다."
        )

    boolean_fields = {
        "paper_execution_authorized": (
            result.paper_execution_authorized
        ),
        "paper_execution_requested": (
            result.paper_execution_requested
        ),
        "paper_fill_created": (
            result.paper_fill_created
        ),
        "live_execution_authorized": (
            result.live_execution_authorized
        ),
        "broker_order_created": (
            result.broker_order_created
        ),
        "live_order_created": (
            result.live_order_created
        ),
        "source_loaded": (
            result.source_loaded
        ),
        "source_valid": (
            result.source_valid
        ),
        "approval_checks_passed": (
            result.approval_checks_passed
        ),
        "policy_checks_passed": (
            result.policy_checks_passed
        ),
        "order_checks_passed": (
            result.order_checks_passed
        ),
        "request_generated": (
            result.request_generated
        ),
        "all_checks_passed": (
            result.all_checks_passed
        ),
        "execution_blocked": (
            result.execution_blocked
        ),
        "paper_execution_pending": (
            result.paper_execution_pending
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
        result.paper_execution_policy
    )


def validate_ready_result(
    result: PaperExecutionRequestResult,
    approval_result: ManualApprovalResult,
) -> None:
    """
    READY_FOR_PAPER 결과를 검사합니다.
    """

    if result.request_status != "READY_FOR_PAPER":
        raise RuntimeError(
            "승인된 요청의 Status가 READY_FOR_PAPER가 아닙니다."
        )

    expected_action = (
        "PAPER_BUY"
        if approval_result.ticket_side == "BUY"
        else "PAPER_SELL"
    )

    if result.request_action != expected_action:
        raise RuntimeError(
            "Request Action이 승인된 Ticket Side와 "
            "일치하지 않습니다."
        )

    if result.approval_status != "APPROVED_FOR_PAPER":
        raise RuntimeError(
            "Result의 Approval Status가 "
            "APPROVED_FOR_PAPER가 아닙니다."
        )

    if result.approval_request != "APPROVE_PAPER":
        raise RuntimeError(
            "Result의 Approval Request가 "
            "APPROVE_PAPER가 아닙니다."
        )

    if result.side != approval_result.ticket_side:
        raise RuntimeError(
            "Result Side가 Manual Approval 결과와 "
            "일치하지 않습니다."
        )

    if result.quantity != approval_result.quantity:
        raise RuntimeError(
            "Result Quantity가 Manual Approval 결과와 "
            "일치하지 않습니다."
        )

    if abs(
        result.reference_price
        - approval_result.reference_price
    ) > 0.0001:
        raise RuntimeError(
            "Result Reference Price가 승인 결과와 "
            "일치하지 않습니다."
        )

    if abs(
        result.estimated_order_value
        - approval_result.estimated_value
    ) > 0.01:
        raise RuntimeError(
            "Result Estimated Order Value가 승인 결과와 "
            "일치하지 않습니다."
        )

    if not result.paper_execution_authorized:
        raise RuntimeError(
            "Paper Execution Authorized가 False입니다."
        )

    if not result.paper_execution_requested:
        raise RuntimeError(
            "Paper Execution Requested가 False입니다."
        )

    if not result.paper_execution_pending:
        raise RuntimeError(
            "Paper Execution Pending이 False입니다."
        )

    if result.paper_fill_created:
        raise RuntimeError(
            "V9.7 단계에서 Paper Fill이 생성되었습니다."
        )

    if result.live_execution_authorized:
        raise RuntimeError(
            "Live Execution이 허용되었습니다."
        )

    if result.broker_order_created:
        raise RuntimeError(
            "Broker Order가 생성되었습니다."
        )

    if result.live_order_created:
        raise RuntimeError(
            "Live Order가 생성되었습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "실제 Execution이 차단되지 않았습니다."
        )

    if result.manual_approval_required:
        raise RuntimeError(
            "승인 완료 후에도 Manual Approval Required가 "
            "True입니다."
        )

    if not result.source_loaded:
        raise RuntimeError(
            "Source Loaded가 False입니다."
        )

    if not result.source_valid:
        raise RuntimeError(
            "Source Valid가 False입니다."
        )

    if not result.approval_checks_passed:
        raise RuntimeError(
            "Approval Checks가 통과되지 않았습니다."
        )

    if not result.policy_checks_passed:
        raise RuntimeError(
            "Policy Checks가 통과되지 않았습니다."
        )

    if not result.order_checks_passed:
        raise RuntimeError(
            "Order Checks가 통과되지 않았습니다."
        )

    if not result.request_generated:
        raise RuntimeError(
            "Request Generated가 False입니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "V9.7 검사가 모두 통과되지 않았습니다."
        )


def validate_execution_safety(
    result: PaperExecutionRequestResult,
) -> None:
    """
    실제 주문 및 실제 체결 안전장치를 검사합니다.
    """

    if result.paper_fill_created:
        raise RuntimeError(
            "V9.7에서 Paper Fill이 생성되었습니다."
        )

    if result.live_execution_authorized:
        raise RuntimeError(
            "V9.7에서 Live Execution이 허용되었습니다."
        )

    if result.broker_order_created:
        raise RuntimeError(
            "V9.7에서 Broker Order가 생성되었습니다."
        )

    if result.live_order_created:
        raise RuntimeError(
            "V9.7에서 Live Order가 생성되었습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "V9.7에서 실제 Execution이 차단되지 않았습니다."
        )

    warning_text = " ".join(
        str(warning)
        for warning in result.warnings
    ).lower()

    if "broker" not in warning_text:
        raise RuntimeError(
            "Warnings에 Broker API 차단 설명이 없습니다."
        )

    if "paper fill" not in warning_text:
        raise RuntimeError(
            "Warnings에 Paper Fill 미생성 설명이 없습니다."
        )

    if "live" not in warning_text:
        raise RuntimeError(
            "Warnings에 Live Execution 차단 설명이 없습니다."
        )


def validate_idempotency_key(
    result: PaperExecutionRequestResult,
    approval_result: ManualApprovalResult,
) -> None:
    """
    Idempotency Key가 입력값에 따라 일정하게 생성되는지 검사합니다.
    """

    expected_key = create_idempotency_key(
        symbol=result.symbol,
        side=approval_result.ticket_side,
        quantity=approval_result.quantity,
        approval_result=approval_result,
    )

    if result.idempotency_key != expected_key:
        raise RuntimeError(
            "Idempotency Key가 Helper 함수 결과와 "
            "일치하지 않습니다."
        )

    second_key = create_idempotency_key(
        symbol=result.symbol,
        side=approval_result.ticket_side,
        quantity=approval_result.quantity,
        approval_result=approval_result,
    )

    if expected_key != second_key:
        raise RuntimeError(
            "동일한 승인 결과에서 Idempotency Key가 "
            "일정하지 않습니다."
        )

    if result.symbol not in result.idempotency_key:
        raise RuntimeError(
            "Idempotency Key에 Symbol이 포함되지 않았습니다."
        )

    if result.side not in result.idempotency_key:
        raise RuntimeError(
            "Idempotency Key에 Side가 포함되지 않았습니다."
        )

    if str(result.quantity) not in result.idempotency_key:
        raise RuntimeError(
            "Idempotency Key에 Quantity가 포함되지 않았습니다."
        )


def validate_request_id_uniqueness(
    first_result: PaperExecutionRequestResult,
    second_result: PaperExecutionRequestResult,
) -> None:
    """
    Request ID는 실행마다 다르고,
    Idempotency Key는 동일 승인에 대해 같은지 검사합니다.
    """

    if first_result.request_id == second_result.request_id:
        raise RuntimeError(
            "서로 다른 Request 결과의 Request ID가 같습니다."
        )

    if (
        first_result.idempotency_key
        != second_result.idempotency_key
    ):
        raise RuntimeError(
            "동일한 승인 결과에서 Idempotency Key가 "
            "변경되었습니다."
        )


def validate_waiting_scenario(
    symbol: str,
    ticket: OrderTicket,
    policy: PaperExecutionPolicy,
) -> PaperExecutionRequestResult:
    """
    WAITING_APPROVAL 시나리오를 검사합니다.
    """

    scenario_time = parse_datetime(
        ticket.created_at
    )

    waiting_approval = run_manual_approval_manager(
        symbol=symbol,
        ticket=ticket,
        approval_request="WAIT",
        approval_actor="TEST_USER",
        approval_note="Waiting approval scenario",
        current_time=scenario_time,
    )

    result = run_paper_execution_request_builder(
        symbol=symbol,
        approval_result=waiting_approval,
        execution_policy=policy,
    )

    if result.request_status != "WAITING_APPROVAL":
        raise RuntimeError(
            "WAIT 시나리오의 Request Status가 "
            "WAITING_APPROVAL이 아닙니다."
        )

    if result.request_action != "NO_ACTION":
        raise RuntimeError(
            "WAIT 시나리오의 Request Action이 "
            "NO_ACTION이 아닙니다."
        )

    if result.request_generated:
        raise RuntimeError(
            "WAIT 시나리오에서 Request가 생성되었습니다."
        )

    if result.paper_execution_authorized:
        raise RuntimeError(
            "WAIT 시나리오에서 Paper Execution이 "
            "허용되었습니다."
        )

    if result.paper_execution_requested:
        raise RuntimeError(
            "WAIT 시나리오에서 Paper Execution이 "
            "요청되었습니다."
        )

    if result.paper_execution_pending:
        raise RuntimeError(
            "WAIT 시나리오에서 Paper Execution Pending이 "
            "True입니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "WAIT 시나리오에서 All Checks Passed가 True입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_rejected_scenario(
    symbol: str,
    ticket: OrderTicket,
    policy: PaperExecutionPolicy,
) -> PaperExecutionRequestResult:
    """
    REJECTED 시나리오를 검사합니다.
    """

    scenario_time = parse_datetime(
        ticket.created_at
    )

    rejected_approval = run_manual_approval_manager(
        symbol=symbol,
        ticket=ticket,
        approval_request="REJECT",
        approval_actor="TEST_USER",
        approval_note="Rejected scenario",
        current_time=scenario_time,
    )

    result = run_paper_execution_request_builder(
        symbol=symbol,
        approval_result=rejected_approval,
        execution_policy=policy,
    )

    if result.request_status != "REJECTED":
        raise RuntimeError(
            "거절 시나리오의 Request Status가 "
            "REJECTED가 아닙니다."
        )

    if result.request_action != "NO_ACTION":
        raise RuntimeError(
            "거절 시나리오의 Request Action이 "
            "NO_ACTION이 아닙니다."
        )

    if result.request_generated:
        raise RuntimeError(
            "거절 시나리오에서 Request가 생성되었습니다."
        )

    if result.paper_execution_authorized:
        raise RuntimeError(
            "거절 시나리오에서 Paper Execution이 "
            "허용되었습니다."
        )

    if result.paper_execution_requested:
        raise RuntimeError(
            "거절 시나리오에서 Paper Execution이 "
            "요청되었습니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "거절 시나리오에서 All Checks Passed가 True입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_expired_scenario(
    symbol: str,
    ticket: OrderTicket,
    policy: PaperExecutionPolicy,
) -> PaperExecutionRequestResult:
    """
    EXPIRED 시나리오를 검사합니다.
    """

    ticket_created_at = parse_datetime(
        ticket.created_at
    )

    expired_time = (
        ticket_created_at
        + timedelta(
            minutes=61,
        )
    )

    expired_approval = run_manual_approval_manager(
        symbol=symbol,
        ticket=ticket,
        approval_request="APPROVE_PAPER",
        approval_actor="TEST_USER",
        approval_note="Expired approval scenario",
        approval_policy=ApprovalPolicy(
            approval_expiration_minutes=60,
        ),
        current_time=expired_time,
    )

    result = run_paper_execution_request_builder(
        symbol=symbol,
        approval_result=expired_approval,
        execution_policy=policy,
    )

    if result.request_status != "EXPIRED":
        raise RuntimeError(
            "만료 시나리오의 Request Status가 "
            "EXPIRED가 아닙니다."
        )

    if result.request_action != "NO_ACTION":
        raise RuntimeError(
            "만료 시나리오의 Request Action이 "
            "NO_ACTION이 아닙니다."
        )

    if result.request_generated:
        raise RuntimeError(
            "만료 시나리오에서 Request가 생성되었습니다."
        )

    if result.paper_execution_authorized:
        raise RuntimeError(
            "만료 시나리오에서 Paper Execution이 "
            "허용되었습니다."
        )

    if result.paper_execution_requested:
        raise RuntimeError(
            "만료 시나리오에서 Paper Execution이 "
            "요청되었습니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "만료 시나리오에서 All Checks Passed가 True입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_blocked_policy_scenario(
    symbol: str,
    approval_result: ManualApprovalResult,
) -> PaperExecutionRequestResult:
    """
    제한적인 Paper Execution Policy로 차단되는지 검사합니다.
    """

    restrictive_maximum_value = max(
        25.0,
        approval_result.estimated_value - 1.0,
    )

    restrictive_policy = PaperExecutionPolicy(
        minimum_quantity=1,
        maximum_quantity=100_000,
        minimum_order_value=25.0,
        maximum_order_value=(
            restrictive_maximum_value
        ),
    )

    result = run_paper_execution_request_builder(
        symbol=symbol,
        approval_result=approval_result,
        execution_policy=restrictive_policy,
    )

    if (
        approval_result.estimated_value
        > restrictive_maximum_value
    ):
        if result.request_status != "BLOCKED":
            raise RuntimeError(
                "제한 정책 시나리오의 Request Status가 "
                "BLOCKED가 아닙니다."
            )

        if result.request_action != "BLOCKED":
            raise RuntimeError(
                "제한 정책 시나리오의 Request Action이 "
                "BLOCKED가 아닙니다."
            )

        if result.request_generated:
            raise RuntimeError(
                "제한 정책 시나리오에서 Request가 "
                "생성되었습니다."
            )

        if result.paper_execution_authorized:
            raise RuntimeError(
                "제한 정책 시나리오에서 Paper Execution이 "
                "허용되었습니다."
            )

        if result.paper_execution_requested:
            raise RuntimeError(
                "제한 정책 시나리오에서 Paper Execution이 "
                "요청되었습니다."
            )

        if result.policy_checks_passed:
            raise RuntimeError(
                "제한 정책 시나리오에서 Policy Checks Passed가 "
                "True입니다."
            )

        if result.all_checks_passed:
            raise RuntimeError(
                "제한 정책 시나리오에서 All Checks Passed가 "
                "True입니다."
            )

    validate_execution_safety(
        result
    )

    return result


def validate_decision_rules(
    approved_result: ManualApprovalResult,
    waiting_result: ManualApprovalResult,
    rejected_result: ManualApprovalResult,
    expired_result: ManualApprovalResult,
) -> None:
    """
    주요 Request Decision 규칙을 직접 검사합니다.
    """

    approved_decision = determine_request_decision(
        approval_result=approved_result,
        source_valid=True,
        approval_checks_passed=True,
        policy_checks_passed=True,
    )

    if approved_decision[0] != "READY_FOR_PAPER":
        raise RuntimeError(
            "승인 Decision 규칙이 READY_FOR_PAPER가 아닙니다."
        )

    if approved_decision[2] not in {
        "PAPER_BUY",
        "PAPER_SELL",
    }:
        raise RuntimeError(
            "승인 Decision Action이 올바르지 않습니다."
        )

    if not approved_decision[4]:
        raise RuntimeError(
            "승인 Decision에서 Request Generated가 False입니다."
        )

    waiting_decision = determine_request_decision(
        approval_result=waiting_result,
        source_valid=True,
        approval_checks_passed=False,
        policy_checks_passed=True,
    )

    if waiting_decision[0] != "WAITING_APPROVAL":
        raise RuntimeError(
            "대기 Decision 규칙이 WAITING_APPROVAL이 아닙니다."
        )

    if waiting_decision[2] != "NO_ACTION":
        raise RuntimeError(
            "대기 Decision Action이 NO_ACTION이 아닙니다."
        )

    if waiting_decision[4]:
        raise RuntimeError(
            "대기 Decision에서 Request가 생성되었습니다."
        )

    rejected_decision = determine_request_decision(
        approval_result=rejected_result,
        source_valid=True,
        approval_checks_passed=False,
        policy_checks_passed=True,
    )

    if rejected_decision[0] != "REJECTED":
        raise RuntimeError(
            "거절 Decision 규칙이 REJECTED가 아닙니다."
        )

    if rejected_decision[4]:
        raise RuntimeError(
            "거절 Decision에서 Request가 생성되었습니다."
        )

    expired_decision = determine_request_decision(
        approval_result=expired_result,
        source_valid=True,
        approval_checks_passed=False,
        policy_checks_passed=True,
    )

    if expired_decision[0] != "EXPIRED":
        raise RuntimeError(
            "만료 Decision 규칙이 EXPIRED가 아닙니다."
        )

    if expired_decision[4]:
        raise RuntimeError(
            "만료 Decision에서 Request가 생성되었습니다."
        )

    failed_decision = determine_request_decision(
        approval_result=approved_result,
        source_valid=False,
        approval_checks_passed=False,
        policy_checks_passed=False,
    )

    if failed_decision[0] != "FAILED":
        raise RuntimeError(
            "Source Invalid Decision이 FAILED가 아닙니다."
        )

    if failed_decision[2] != "BLOCKED":
        raise RuntimeError(
            "Source Invalid Action이 BLOCKED가 아닙니다."
        )

    if failed_decision[4]:
        raise RuntimeError(
            "Source Invalid 상태에서 Request가 생성되었습니다."
        )


def validate_saved_files(
    result: PaperExecutionRequestResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    저장된 V9.7 JSON 파일을 검사합니다.
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
            "저장된 JSON 내용이 V9.7 실행 결과와 "
            "일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "request_id",
        "idempotency_key",
        "source_manual_approval_file",
        "request_status",
        "request_status_label",
        "request_action",
        "request_action_label",
        "approval_status",
        "approval_request",
        "approval_actor",
        "approved_at",
        "side",
        "quantity",
        "order_type",
        "time_in_force",
        "reference_price",
        "requested_price",
        "estimated_order_value",
        "paper_execution_authorized",
        "paper_execution_requested",
        "paper_fill_created",
        "live_execution_authorized",
        "broker_order_created",
        "live_order_created",
        "source_loaded",
        "source_valid",
        "approval_checks_passed",
        "policy_checks_passed",
        "order_checks_passed",
        "request_generated",
        "all_checks_passed",
        "execution_blocked",
        "paper_execution_pending",
        "manual_approval_required",
        "paper_execution_policy",
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
            "저장된 V9.7 JSON에 필수 키가 없습니다: "
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
    ready_result: PaperExecutionRequestResult,
    duplicate_result: PaperExecutionRequestResult,
    waiting_result: PaperExecutionRequestResult,
    rejected_result: PaperExecutionRequestResult,
    expired_result: PaperExecutionRequestResult,
    blocked_result: PaperExecutionRequestResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.7 주요 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V9.7 PAPER EXECUTION REQUEST BUILDER "
        "TEST RESULT"
    )
    print("=" * 140)

    print("READY FOR PAPER")
    print("-" * 140)

    print(
        f"Request status                 : "
        f"{ready_result.request_status}"
    )

    print(
        f"Request action                 : "
        f"{ready_result.request_action}"
    )

    print(
        f"Side                           : "
        f"{ready_result.side}"
    )

    print(
        f"Quantity                       : "
        f"{ready_result.quantity}"
    )

    print(
        f"Reference price                : "
        f"${ready_result.reference_price:,.2f}"
    )

    print(
        f"Estimated order value          : "
        f"${ready_result.estimated_order_value:,.2f}"
    )

    print(
        f"Paper execution authorized     : "
        f"{ready_result.paper_execution_authorized}"
    )

    print(
        f"Paper execution requested      : "
        f"{ready_result.paper_execution_requested}"
    )

    print(
        f"Paper execution pending        : "
        f"{ready_result.paper_execution_pending}"
    )

    print()
    print("IDEMPOTENCY")
    print("-" * 140)

    print(
        f"First request ID               : "
        f"{ready_result.request_id}"
    )

    print(
        f"Second request ID              : "
        f"{duplicate_result.request_id}"
    )

    print(
        f"Idempotency key                : "
        f"{ready_result.idempotency_key}"
    )

    print(
        f"Request IDs are different      : "
        f"{ready_result.request_id != duplicate_result.request_id}"
    )

    print(
        f"Idempotency keys match         : "
        f"{ready_result.idempotency_key == duplicate_result.idempotency_key}"
    )

    print()
    print("NON-EXECUTABLE SCENARIOS")
    print("-" * 140)

    print(
        f"Waiting status                 : "
        f"{waiting_result.request_status}"
    )

    print(
        f"Rejected status                : "
        f"{rejected_result.request_status}"
    )

    print(
        f"Expired status                 : "
        f"{expired_result.request_status}"
    )

    print(
        f"Blocked status                 : "
        f"{blocked_result.request_status}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Paper fill created             : "
        f"{ready_result.paper_fill_created}"
    )

    print(
        f"Live execution authorized      : "
        f"{ready_result.live_execution_authorized}"
    )

    print(
        f"Broker order created           : "
        f"{ready_result.broker_order_created}"
    )

    print(
        f"Live order created             : "
        f"{ready_result.live_order_created}"
    )

    print(
        f"Execution blocked              : "
        f"{ready_result.execution_blocked}"
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
    ready_result: PaperExecutionRequestResult,
    duplicate_result: PaperExecutionRequestResult,
    waiting_result: PaperExecutionRequestResult,
    rejected_result: PaperExecutionRequestResult,
    expired_result: PaperExecutionRequestResult,
    blocked_result: PaperExecutionRequestResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True 또는 False로 출력합니다.
    """

    checks = {
        "Version is V9.7": (
            ready_result.version == "V9.7"
        ),
        "Request status is READY_FOR_PAPER": (
            ready_result.request_status
            == "READY_FOR_PAPER"
        ),
        "Request action is valid": (
            ready_result.request_action
            in {
                "PAPER_BUY",
                "PAPER_SELL",
            }
        ),
        "Side is valid": (
            ready_result.side
            in {
                "BUY",
                "SELL",
            }
        ),
        "Quantity is positive": (
            ready_result.quantity > 0
        ),
        "Reference price is positive": (
            ready_result.reference_price > 0
        ),
        "Estimated order value is positive": (
            ready_result.estimated_order_value > 0
        ),
        "Approval status matches": (
            ready_result.approval_status
            == "APPROVED_FOR_PAPER"
        ),
        "Approval request matches": (
            ready_result.approval_request
            == "APPROVE_PAPER"
        ),
        "Source loaded": (
            ready_result.source_loaded
        ),
        "Source valid": (
            ready_result.source_valid
        ),
        "Approval checks passed": (
            ready_result.approval_checks_passed
        ),
        "Policy checks passed": (
            ready_result.policy_checks_passed
        ),
        "Order checks passed": (
            ready_result.order_checks_passed
        ),
        "Request generated": (
            ready_result.request_generated
        ),
        "All checks passed": (
            ready_result.all_checks_passed
        ),
        "Paper execution authorized": (
            ready_result.paper_execution_authorized
        ),
        "Paper execution requested": (
            ready_result.paper_execution_requested
        ),
        "Paper execution pending": (
            ready_result.paper_execution_pending
        ),
        "Paper fill not created": (
            not ready_result.paper_fill_created
        ),
        "Live execution not authorized": (
            not ready_result.live_execution_authorized
        ),
        "Broker order not created": (
            not ready_result.broker_order_created
        ),
        "Live order not created": (
            not ready_result.live_order_created
        ),
        "Execution remains blocked": (
            ready_result.execution_blocked
        ),
        "Request ID exists": bool(
            ready_result.request_id
        ),
        "Idempotency key exists": bool(
            ready_result.idempotency_key
        ),
        "Duplicate request ID differs": (
            ready_result.request_id
            != duplicate_result.request_id
        ),
        "Duplicate idempotency key matches": (
            ready_result.idempotency_key
            == duplicate_result.idempotency_key
        ),
        "Waiting scenario is valid": (
            waiting_result.request_status
            == "WAITING_APPROVAL"
        ),
        "Waiting request not generated": (
            not waiting_result.request_generated
        ),
        "Rejected scenario is valid": (
            rejected_result.request_status
            == "REJECTED"
        ),
        "Rejected request not generated": (
            not rejected_result.request_generated
        ),
        "Expired scenario is valid": (
            expired_result.request_status
            == "EXPIRED"
        ),
        "Expired request not generated": (
            not expired_result.request_generated
        ),
        "Blocked scenario is valid": (
            blocked_result.request_status
            == "BLOCKED"
        ),
        "Blocked request not generated": (
            not blocked_result.request_generated
        ),
        "Policy is immutable": True,
        "Reasons exist": bool(
            ready_result.reasons
        ),
        "Warnings exist": bool(
            ready_result.warnings
        ),
        "Next actions exist": bool(
            ready_result.next_actions
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
    V9.7 Paper Execution Request Builder 통합 테스트입니다.

    테스트 내용:

    1. V9.4 Position Sizing 생성
    2. V9.5 Order Ticket 생성
    3. V9.6 APPROVE_PAPER 승인
    4. V9.7 READY_FOR_PAPER 요청 생성
    5. Idempotency Key 검증
    6. WAITING_APPROVAL 검증
    7. REJECTED 검증
    8. EXPIRED 검증
    9. 제한 정책 BLOCKED 검증
    10. 실제 주문 및 체결 차단
    11. JSON 저장 검증
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

        validate_position_sizing_result(
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

        validate_order_ticket(
            ticket=ticket,
            sizing_result=sizing_result,
        )

        execution_policy = PaperExecutionPolicy()

        validate_policy_structure(
            execution_policy
        )

        validate_policy_is_immutable(
            execution_policy
        )

        validate_normal_policy(
            execution_policy
        )

        validate_invalid_policies()

        scenario_time = parse_datetime(
            ticket.created_at
        )

        approved_result = run_manual_approval_manager(
            symbol=symbol,
            ticket=ticket,
            approval_request="APPROVE_PAPER",
            approval_actor="TEST_USER",
            approval_note=(
                "V9.7 paper execution request integration test"
            ),
            current_time=scenario_time,
        )

        (
            approval_report_path,
            approval_latest_path,
        ) = save_manual_approval_manager(
            approved_result
        )

        if not approval_report_path.exists():
            raise RuntimeError(
                "V9.6 Manual Approval Report 파일이 없습니다."
            )

        if not approval_latest_path.exists():
            raise RuntimeError(
                "V9.6 Manual Approval Latest 파일이 없습니다."
            )

        validate_manual_approval_source(
            approved_result
        )

        validate_approved_manual_result(
            approved_result
        )

        validate_approved_result_against_policy(
            approval_result=approved_result,
            policy=execution_policy,
        )

        ready_result = (
            run_paper_execution_request_builder(
                symbol=symbol,
                approval_result=approved_result,
                execution_policy=execution_policy,
            )
        )

        validate_result_structure(
            ready_result
        )

        validate_ready_result(
            result=ready_result,
            approval_result=approved_result,
        )

        validate_execution_safety(
            ready_result
        )

        validate_idempotency_key(
            result=ready_result,
            approval_result=approved_result,
        )

        duplicate_result = (
            run_paper_execution_request_builder(
                symbol=symbol,
                approval_result=approved_result,
                execution_policy=execution_policy,
            )
        )

        validate_result_structure(
            duplicate_result
        )

        validate_ready_result(
            result=duplicate_result,
            approval_result=approved_result,
        )

        validate_request_id_uniqueness(
            first_result=ready_result,
            second_result=duplicate_result,
        )

        waiting_result = validate_waiting_scenario(
            symbol=symbol,
            ticket=ticket,
            policy=execution_policy,
        )

        rejected_result = validate_rejected_scenario(
            symbol=symbol,
            ticket=ticket,
            policy=execution_policy,
        )

        expired_result = validate_expired_scenario(
            symbol=symbol,
            ticket=ticket,
            policy=execution_policy,
        )

        blocked_result = (
            validate_blocked_policy_scenario(
                symbol=symbol,
                approval_result=approved_result,
            )
        )

        waiting_approval_for_rules = (
            run_manual_approval_manager(
                symbol=symbol,
                ticket=ticket,
                approval_request="WAIT",
                approval_actor="TEST_USER",
                current_time=scenario_time,
            )
        )

        rejected_approval_for_rules = (
            run_manual_approval_manager(
                symbol=symbol,
                ticket=ticket,
                approval_request="REJECT",
                approval_actor="TEST_USER",
                current_time=scenario_time,
            )
        )

        expired_approval_for_rules = (
            run_manual_approval_manager(
                symbol=symbol,
                ticket=ticket,
                approval_request="APPROVE_PAPER",
                approval_actor="TEST_USER",
                approval_policy=ApprovalPolicy(
                    approval_expiration_minutes=60,
                ),
                current_time=(
                    scenario_time
                    + timedelta(
                        minutes=61,
                    )
                ),
            )
        )

        validate_decision_rules(
            approved_result=approved_result,
            waiting_result=waiting_approval_for_rules,
            rejected_result=rejected_approval_for_rules,
            expired_result=expired_approval_for_rules,
        )

        (
            report_path,
            latest_path,
        ) = save_paper_execution_request(
            ready_result
        )

        validate_saved_files(
            result=ready_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_test_result(
            ready_result=ready_result,
            duplicate_result=duplicate_result,
            waiting_result=waiting_result,
            rejected_result=rejected_result,
            expired_result=expired_result,
            blocked_result=blocked_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_validation_checks(
            ready_result=ready_result,
            duplicate_result=duplicate_result,
            waiting_result=waiting_result,
            rejected_result=rejected_result,
            expired_result=expired_result,
            blocked_result=blocked_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V9.7 paper execution request builder "
            "test completed successfully."
        )

        print(
            f"승인된 요청 상태는 "
            f"{ready_result.request_status}이며 "
            f"요청 행동은 "
            f"{ready_result.request_action}입니다."
        )

        print(
            f"가상 주문 요청 수량은 "
            f"{ready_result.quantity}주이며 "
            f"예상 주문 금액은 "
            f"${ready_result.estimated_order_value:,.2f}입니다."
        )

        print(
            "동일 승인 결과의 Request ID는 각각 다르지만 "
            "Idempotency Key는 동일하게 유지되었습니다."
        )

        print(
            "WAITING_APPROVAL, REJECTED, EXPIRED 및 "
            "BLOCKED 상태에서는 Paper Request가 "
            "생성되지 않았습니다."
        )

        print(
            "Paper Fill, Broker Order 및 Live Order는 "
            "모두 생성되지 않았습니다."
        )

        print(
            "주의: 이 결과는 연구용 가상 주문 요청서이며 "
            "실제 증권 주문이나 체결이 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V9.7 Paper Execution Request Builder "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V9.7 PAPER EXECUTION REQUEST BUILDER ERROR"
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