import json
import math
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.manual_approval_manager import (
    ApprovalPolicy,
    ManualApprovalResult,
    run_manual_approval_manager,
    save_manual_approval_manager,
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


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_EXECUTION_REQUEST_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_execution_request"
)


VALID_REQUEST_STATUSES = {
    "READY_FOR_PAPER",
    "WAITING_APPROVAL",
    "REJECTED",
    "EXPIRED",
    "BLOCKED",
    "NO_ACTION",
    "FAILED",
}


VALID_REQUEST_ACTIONS = {
    "PAPER_BUY",
    "PAPER_SELL",
    "NO_ACTION",
    "BLOCKED",
}


VALID_SIDES = {
    "BUY",
    "SELL",
    "NONE",
}


VALID_ORDER_TYPES = {
    "MARKET",
    "LIMIT",
}


VALID_TIME_IN_FORCE = {
    "DAY",
    "GTC",
}


@dataclass(frozen=True)
class PaperExecutionPolicy:
    """
    Paper Execution Request 생성 안전 정책입니다.

    이 정책은 실제 Broker 주문과 관계가 없으며
    연구용 가상 주문 요청만 제한합니다.
    """

    minimum_quantity: int = 1
    maximum_quantity: int = 100_000

    minimum_order_value: float = 25.0
    maximum_order_value: float = 1_000_000.0

    allow_buy: bool = True
    allow_sell: bool = True

    allow_market_order: bool = True
    allow_limit_order: bool = False

    paper_only: bool = True
    live_execution_disabled: bool = True
    require_manual_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperExecutionRequestResult:
    """
    V9.7 Paper Execution Request Builder 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    request_id: str
    idempotency_key: str

    source_manual_approval_file: str | None

    request_status: str
    request_status_label: str
    request_action: str
    request_action_label: str

    approval_status: str
    approval_request: str
    approval_actor: str
    approved_at: str | None

    side: str
    quantity: int

    order_type: str
    time_in_force: str

    reference_price: float
    requested_price: float | None
    estimated_order_value: float

    paper_execution_authorized: bool
    paper_execution_requested: bool
    paper_fill_created: bool

    live_execution_authorized: bool
    broker_order_created: bool
    live_order_created: bool

    source_loaded: bool
    source_valid: bool
    approval_checks_passed: bool
    policy_checks_passed: bool
    order_checks_passed: bool
    request_generated: bool
    all_checks_passed: bool

    execution_blocked: bool
    paper_execution_pending: bool
    manual_approval_required: bool

    paper_execution_policy: PaperExecutionPolicy

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["paper_execution_policy"] = (
            self.paper_execution_policy.to_dict()
        )

        return payload


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정규화합니다.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def is_valid_number(
    value: Any,
) -> bool:
    """
    유한한 숫자인지 검사합니다.
    """

    if isinstance(value, bool):
        return False

    try:
        numeric_value = float(value)

    except (TypeError, ValueError):
        return False

    return math.isfinite(numeric_value)


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일 방식으로 안전하게 저장합니다.
    """

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    with temporary_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    temporary_path.replace(file_path)


def validate_paper_execution_policy(
    policy: PaperExecutionPolicy,
) -> tuple[bool, list[str]]:
    """
    Paper Execution Policy를 검사합니다.
    """

    errors: list[str] = []

    if not (
        1
        <= policy.minimum_quantity
        <= policy.maximum_quantity
    ):
        errors.append(
            "Minimum Quantity와 Maximum Quantity가 올바르지 않습니다."
        )

    if not (
        0.0
        < policy.minimum_order_value
        <= policy.maximum_order_value
    ):
        errors.append(
            "Minimum Order Value와 Maximum Order Value가 "
            "올바르지 않습니다."
        )

    boolean_fields = {
        "allow_buy": policy.allow_buy,
        "allow_sell": policy.allow_sell,
        "allow_market_order": policy.allow_market_order,
        "allow_limit_order": policy.allow_limit_order,
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
        "require_manual_approval": (
            policy.require_manual_approval
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(value, bool):
            errors.append(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if not policy.paper_only:
        errors.append(
            "V9.7에서는 Paper Only가 반드시 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V9.7에서는 Live Execution Disabled가 "
            "반드시 True여야 합니다."
        )

    if not policy.require_manual_approval:
        errors.append(
            "V9.7에서는 수동 승인이 반드시 필요합니다."
        )

    return (
        not errors,
        errors,
    )


def validate_manual_approval_result(
    approval_result: ManualApprovalResult,
) -> tuple[bool, list[str]]:
    """
    V9.6 Manual Approval 결과를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        approval_result,
        ManualApprovalResult,
    ):
        errors.append(
            "Manual Approval Result 형식이 올바르지 않습니다."
        )

        return (
            False,
            errors,
        )

    if approval_result.version != "V9.6":
        errors.append(
            "Manual Approval Result 버전이 V9.6이 아닙니다."
        )

    if not approval_result.symbol:
        errors.append(
            "Manual Approval Symbol이 비어 있습니다."
        )

    if not approval_result.source_loaded:
        errors.append(
            "V9.6 Source Loaded가 False입니다."
        )

    if not approval_result.source_valid:
        errors.append(
            "V9.6 Source Valid가 False입니다."
        )

    if not approval_result.ticket_checks_passed:
        errors.append(
            "V9.6 Ticket Checks가 통과되지 않았습니다."
        )

    if not approval_result.expiration_checks_passed:
        errors.append(
            "V9.6 Expiration Checks가 통과되지 않았습니다."
        )

    if not approval_result.policy_checks_passed:
        errors.append(
            "V9.6 Policy Checks가 통과되지 않았습니다."
        )

    if not approval_result.decision_generated:
        errors.append(
            "V9.6 Approval Decision이 생성되지 않았습니다."
        )

    if not approval_result.all_checks_passed:
        errors.append(
            "V9.6 검사가 모두 통과되지 않았습니다."
        )

    if approval_result.ticket_side not in VALID_SIDES:
        errors.append(
            "V9.6 Ticket Side가 올바르지 않습니다."
        )

    if approval_result.order_type not in VALID_ORDER_TYPES:
        errors.append(
            "V9.6 Order Type이 올바르지 않습니다."
        )

    if (
        approval_result.time_in_force
        not in VALID_TIME_IN_FORCE
    ):
        errors.append(
            "V9.6 Time In Force가 올바르지 않습니다."
        )

    if not isinstance(
        approval_result.quantity,
        int,
    ):
        errors.append(
            "V9.6 Quantity가 int 형식이 아닙니다."
        )

    elif approval_result.quantity < 0:
        errors.append(
            "V9.6 Quantity가 음수입니다."
        )

    if not is_valid_number(
        approval_result.reference_price
    ):
        errors.append(
            "Reference Price가 유효한 숫자가 아닙니다."
        )

    elif approval_result.reference_price <= 0:
        errors.append(
            "Reference Price가 0 이하입니다."
        )

    if not is_valid_number(
        approval_result.estimated_value
    ):
        errors.append(
            "Estimated Value가 유효한 숫자가 아닙니다."
        )

    elif approval_result.estimated_value < 0:
        errors.append(
            "Estimated Value가 음수입니다."
        )

    expected_value = round(
        approval_result.quantity
        * approval_result.reference_price,
        2,
    )

    if abs(
        approval_result.estimated_value
        - expected_value
    ) > 0.01:
        errors.append(
            "Estimated Value 계산이 일치하지 않습니다."
        )

    if not approval_result.execution_blocked:
        errors.append(
            "V9.6에서 Execution이 차단되지 않았습니다."
        )

    if approval_result.order_generated:
        errors.append(
            "V9.6에서 Order가 생성되었습니다."
        )

    if approval_result.broker_order_generated:
        errors.append(
            "V9.6에서 Broker Order가 생성되었습니다."
        )

    if approval_result.paper_order_generated:
        errors.append(
            "V9.6에서 Paper Order가 생성되었습니다."
        )

    if approval_result.live_order_generated:
        errors.append(
            "V9.6에서 Live Order가 생성되었습니다."
        )

    return (
        not errors,
        errors,
    )


def validate_approval_for_request(
    approval_result: ManualApprovalResult,
) -> tuple[bool, list[str]]:
    """
    Paper Execution Request 생성 권한을 검사합니다.
    """

    errors: list[str] = []

    if (
        approval_result.approval_status
        != "APPROVED_FOR_PAPER"
    ):
        errors.append(
            "Approval Status가 APPROVED_FOR_PAPER가 아닙니다."
        )

    if not approval_result.approved:
        errors.append(
            "Approved Flag가 False입니다."
        )

    if approval_result.rejected:
        errors.append(
            "승인 결과가 Rejected 상태입니다."
        )

    if approval_result.expired:
        errors.append(
            "승인 결과가 Expired 상태입니다."
        )

    if approval_result.blocked:
        errors.append(
            "승인 결과가 Blocked 상태입니다."
        )

    if not approval_result.paper_execution_allowed:
        errors.append(
            "Paper Execution Allowed가 False입니다."
        )

    if approval_result.live_execution_allowed:
        errors.append(
            "Live Execution Allowed가 True입니다."
        )

    if approval_result.approved_at is None:
        errors.append(
            "Approved At이 기록되지 않았습니다."
        )

    return (
        not errors,
        errors,
    )


def validate_request_against_policy(
    approval_result: ManualApprovalResult,
    policy: PaperExecutionPolicy,
) -> tuple[bool, list[str]]:
    """
    승인된 티켓이 Paper Execution 정책에 맞는지 검사합니다.
    """

    errors: list[str] = []

    if approval_result.ticket_side == "BUY":
        if not policy.allow_buy:
            errors.append(
                "Paper Execution Policy에서 BUY가 허용되지 않습니다."
            )

    elif approval_result.ticket_side == "SELL":
        if not policy.allow_sell:
            errors.append(
                "Paper Execution Policy에서 SELL이 허용되지 않습니다."
            )

    else:
        errors.append(
            "Side가 NONE인 티켓은 Paper Request를 "
            "생성할 수 없습니다."
        )

    if approval_result.order_type == "MARKET":
        if not policy.allow_market_order:
            errors.append(
                "Market Order가 정책상 허용되지 않습니다."
            )

    elif approval_result.order_type == "LIMIT":
        if not policy.allow_limit_order:
            errors.append(
                "Limit Order가 정책상 허용되지 않습니다."
            )

    if not (
        policy.minimum_quantity
        <= approval_result.quantity
        <= policy.maximum_quantity
    ):
        errors.append(
            "Quantity가 Paper Execution 정책 범위를 벗어났습니다."
        )

    if not (
        policy.minimum_order_value
        <= approval_result.estimated_value
        <= policy.maximum_order_value
    ):
        errors.append(
            "Estimated Order Value가 정책 범위를 벗어났습니다."
        )

    return (
        not errors,
        errors,
    )


def determine_request_decision(
    approval_result: ManualApprovalResult,
    source_valid: bool,
    approval_checks_passed: bool,
    policy_checks_passed: bool,
) -> tuple[
    str,
    str,
    str,
    str,
    bool,
    list[str],
]:
    """
    승인 결과를 Paper Execution Request 상태로 변환합니다.
    """

    if not source_valid:
        return (
            "FAILED",
            "승인 결과 검사 실패",
            "BLOCKED",
            "요청 생성 실패",
            False,
            [
                "V9.6 승인 결과가 유효하지 않습니다.",
                "Paper Execution Request를 생성하지 않습니다.",
            ],
        )

    if approval_result.approval_status == "WAITING_APPROVAL":
        return (
            "WAITING_APPROVAL",
            "수동 승인 대기",
            "NO_ACTION",
            "승인 전 요청 없음",
            False,
            [
                "수동 승인이 아직 완료되지 않았습니다.",
                "Paper Execution Request를 생성하지 않습니다.",
            ],
        )

    if approval_result.approval_status == "REJECTED":
        return (
            "REJECTED",
            "승인 거절",
            "NO_ACTION",
            "거절된 요청",
            False,
            [
                "사용자가 주문 티켓을 거절했습니다.",
                "Paper Execution Request를 생성하지 않습니다.",
            ],
        )

    if approval_result.approval_status == "EXPIRED":
        return (
            "EXPIRED",
            "승인 유효시간 만료",
            "NO_ACTION",
            "만료된 요청",
            False,
            [
                "승인 티켓이 만료되었습니다.",
                "최신 데이터로 주문 티켓을 다시 생성해야 합니다.",
            ],
        )

    if approval_result.approval_status == "BLOCKED":
        return (
            "BLOCKED",
            "승인 단계에서 차단",
            "BLOCKED",
            "요청 생성 차단",
            False,
            [
                "V9.6 승인 단계에서 차단되었습니다.",
                "Paper Execution Request를 생성하지 않습니다.",
            ],
        )

    if not (
        approval_checks_passed
        and policy_checks_passed
    ):
        return (
            "BLOCKED",
            "요청 안전검사 실패",
            "BLOCKED",
            "요청 생성 차단",
            False,
            [
                "승인 또는 정책 검사가 통과되지 않았습니다.",
                "Paper Execution Request를 생성하지 않습니다.",
            ],
        )

    if approval_result.ticket_side == "BUY":
        return (
            "READY_FOR_PAPER",
            "Paper 매수 요청 준비 완료",
            "PAPER_BUY",
            "가상 매수 요청",
            True,
            [
                "Paper Trading용 BUY 승인이 확인되었습니다.",
                "가상 매수 요청서를 생성합니다.",
            ],
        )

    if approval_result.ticket_side == "SELL":
        return (
            "READY_FOR_PAPER",
            "Paper 매도 요청 준비 완료",
            "PAPER_SELL",
            "가상 매도 요청",
            True,
            [
                "Paper Trading용 SELL 승인이 확인되었습니다.",
                "가상 매도 요청서를 생성합니다.",
            ],
        )

    return (
        "NO_ACTION",
        "실행할 주문 없음",
        "NO_ACTION",
        "요청 없음",
        False,
        [
            "실행할 수 있는 BUY 또는 SELL Side가 없습니다.",
        ],
    )


def create_idempotency_key(
    symbol: str,
    side: str,
    quantity: int,
    approval_result: ManualApprovalResult,
) -> str:
    """
    동일한 승인 결과의 중복 요청을 방지하기 위한 키를 생성합니다.
    """

    approved_timestamp = (
        approval_result.approved_at
        or approval_result.created_at
    )

    normalized_timestamp = (
        approved_timestamp
        .replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace("T", "_")
    )

    return (
        f"{symbol}_"
        f"{side}_"
        f"{quantity}_"
        f"{normalized_timestamp}"
    )


def build_request_notes(
    request_status: str,
    source_errors: list[str],
    approval_errors: list[str],
    policy_errors: list[str],
) -> tuple[list[str], list[str]]:
    """
    경고와 다음 단계를 생성합니다.
    """

    warnings: list[str] = []

    warnings.extend(source_errors)
    warnings.extend(approval_errors)
    warnings.extend(policy_errors)

    warnings.extend(
        [
            (
                "이 요청서는 연구용 Paper Trading 요청이며 "
                "실제 증권 주문이 아닙니다."
            ),
            (
                "V9.7은 Broker API 또는 실제 계좌 API를 "
                "호출하지 않습니다."
            ),
            (
                "Paper Fill은 아직 생성되지 않았습니다."
            ),
            (
                "Live Execution은 항상 차단됩니다."
            ),
        ]
    )

    if request_status == "READY_FOR_PAPER":
        next_actions = [
            (
                "V9.8 Paper Broker Simulator로 요청서를 전달합니다."
            ),
            (
                "가상 계좌 현금과 보유 수량을 다시 검사합니다."
            ),
            (
                "동일한 Idempotency Key가 이미 처리되었는지 "
                "확인합니다."
            ),
            (
                "가상 체결 후에도 실제 Broker에는 "
                "전송하지 않습니다."
            ),
        ]

    elif request_status == "WAITING_APPROVAL":
        next_actions = [
            (
                "V9.6에서 APPROVE_PAPER 또는 REJECT를 "
                "선택합니다."
            ),
            (
                "승인 전에는 Paper Execution Request를 "
                "처리하지 않습니다."
            ),
        ]

    elif request_status == "EXPIRED":
        next_actions = [
            (
                "최신 시장 데이터로 신호와 티켓을 다시 생성합니다."
            ),
            (
                "새로운 티켓을 다시 수동 승인합니다."
            ),
        ]

    elif request_status == "REJECTED":
        next_actions = [
            (
                "거절된 티켓을 종료 처리합니다."
            ),
            (
                "새로운 분석 결과가 나올 때까지 기다립니다."
            ),
        ]

    else:
        next_actions = [
            (
                "Paper Execution Request 생성을 중단합니다."
            ),
            (
                "승인 결과와 정책 오류를 확인합니다."
            ),
            (
                "검사가 통과되기 전 다음 단계로 전달하지 않습니다."
            ),
        ]

    return (
        warnings,
        next_actions,
    )


def run_paper_execution_request_builder(
    symbol: str = "AAPL",
    approval_result: ManualApprovalResult | None = None,
    ticket: OrderTicket | None = None,
    sizing_result: PositionSizingResult | None = None,
    approval_policy: ApprovalPolicy | None = None,
    execution_policy: PaperExecutionPolicy | None = None,
    approval_actor: str = "MANUAL_USER",
    approval_note: str | None = None,
    account_cash: float = 10_000.0,
) -> PaperExecutionRequestResult:
    """
    V9.6 승인 결과를 이용해 Paper Execution Request를 생성합니다.

    기본 실행에서는 APPROVE_PAPER 승인을 생성합니다.

    이 함수는 가상 체결이나 실제 주문을 실행하지 않습니다.
    """

    normalized_symbol = normalize_symbol(symbol)

    policy = (
        execution_policy
        if execution_policy is not None
        else PaperExecutionPolicy()
    )

    (
        policy_valid,
        policy_errors,
    ) = validate_paper_execution_policy(
        policy
    )

    if approval_result is None:
        if ticket is None:
            if sizing_result is None:
                sizing_result = run_position_sizing_manager(
                    symbol=normalized_symbol,
                    account_cash=account_cash,
                )

                save_position_sizing_manager(
                    sizing_result
                )

            ticket = build_order_ticket(
                sizing_result
            )

            save_order_ticket(ticket)

        approval_result = run_manual_approval_manager(
            symbol=normalized_symbol,
            ticket=ticket,
            approval_request="APPROVE_PAPER",
            approval_actor=approval_actor,
            approval_note=approval_note,
            approval_policy=approval_policy,
        )

        save_manual_approval_manager(
            approval_result
        )

    if approval_result.symbol != normalized_symbol:
        raise ValueError(
            "Manual Approval Symbol과 요청 Symbol이 "
            "일치하지 않습니다."
        )

    (
        source_valid,
        source_errors,
    ) = validate_manual_approval_result(
        approval_result
    )

    (
        approval_checks_passed,
        approval_errors,
    ) = validate_approval_for_request(
        approval_result
    )

    (
        request_policy_valid,
        request_policy_errors,
    ) = validate_request_against_policy(
        approval_result=approval_result,
        policy=policy,
    )

    policy_errors.extend(
        request_policy_errors
    )

    policy_checks_passed = (
        policy_valid
        and request_policy_valid
    )

    (
        request_status,
        request_status_label,
        request_action,
        request_action_label,
        request_generated,
        decision_reasons,
    ) = determine_request_decision(
        approval_result=approval_result,
        source_valid=source_valid,
        approval_checks_passed=(
            approval_checks_passed
        ),
        policy_checks_passed=(
            policy_checks_passed
        ),
    )

    order_checks_passed = (
        approval_result.ticket_side
        in VALID_SIDES
        and approval_result.order_type
        in VALID_ORDER_TYPES
        and approval_result.time_in_force
        in VALID_TIME_IN_FORCE
        and isinstance(
            approval_result.quantity,
            int,
        )
        and approval_result.quantity >= 0
        and is_valid_number(
            approval_result.reference_price
        )
        and approval_result.reference_price > 0
        and is_valid_number(
            approval_result.estimated_value
        )
        and approval_result.estimated_value >= 0
    )

    paper_execution_authorized = (
        request_status == "READY_FOR_PAPER"
        and request_generated
        and approval_checks_passed
        and policy_checks_passed
        and order_checks_passed
        and policy.paper_only
    )

    paper_execution_requested = (
        paper_execution_authorized
    )

    all_checks_passed = (
        source_valid
        and approval_checks_passed
        and policy_checks_passed
        and order_checks_passed
        and request_generated
        and paper_execution_authorized
    )

    request_id = str(
        uuid.uuid4()
    )

    idempotency_key = create_idempotency_key(
        symbol=normalized_symbol,
        side=approval_result.ticket_side,
        quantity=approval_result.quantity,
        approval_result=approval_result,
    )

    requested_price: float | None = None

    if approval_result.order_type == "LIMIT":
        requested_price = float(
            approval_result.reference_price
        )

    reasons: list[str] = []

    reasons.extend(decision_reasons)

    reasons.extend(
        [
            (
                f"승인 상태는 "
                f"{approval_result.approval_status}입니다."
            ),
            (
                f"요청 Side는 "
                f"{approval_result.ticket_side}입니다."
            ),
            (
                f"요청 수량은 "
                f"{approval_result.quantity}주입니다."
            ),
            (
                f"참조 가격은 "
                f"${approval_result.reference_price:,.2f}입니다."
            ),
            (
                f"예상 주문 금액은 "
                f"${approval_result.estimated_value:,.2f}입니다."
            ),
        ]
    )

    (
        warnings,
        next_actions,
    ) = build_request_notes(
        request_status=request_status,
        source_errors=source_errors,
        approval_errors=approval_errors,
        policy_errors=policy_errors,
    )

    result = PaperExecutionRequestResult(
        version="V9.7",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        request_id=request_id,
        idempotency_key=idempotency_key,

        source_manual_approval_file=(
            approval_result.latest_path
            or approval_result.report_path
            or approval_result.source_order_ticket_file
        ),

        request_status=request_status,
        request_status_label=(
            request_status_label
        ),
        request_action=request_action,
        request_action_label=(
            request_action_label
        ),

        approval_status=(
            approval_result.approval_status
        ),
        approval_request=(
            approval_result.approval_request
        ),
        approval_actor=(
            approval_result.approval_actor
        ),
        approved_at=(
            approval_result.approved_at
        ),

        side=approval_result.ticket_side,
        quantity=int(
            approval_result.quantity
        ),

        order_type=(
            approval_result.order_type
        ),
        time_in_force=(
            approval_result.time_in_force
        ),

        reference_price=float(
            approval_result.reference_price
        ),
        requested_price=requested_price,
        estimated_order_value=float(
            approval_result.estimated_value
        ),

        paper_execution_authorized=(
            paper_execution_authorized
        ),
        paper_execution_requested=(
            paper_execution_requested
        ),
        paper_fill_created=False,

        live_execution_authorized=False,
        broker_order_created=False,
        live_order_created=False,

        source_loaded=True,
        source_valid=source_valid,
        approval_checks_passed=(
            approval_checks_passed
        ),
        policy_checks_passed=(
            policy_checks_passed
        ),
        order_checks_passed=(
            order_checks_passed
        ),
        request_generated=(
            request_generated
        ),
        all_checks_passed=(
            all_checks_passed
        ),

        execution_blocked=True,
        paper_execution_pending=(
            paper_execution_requested
        ),
        manual_approval_required=False,

        paper_execution_policy=policy,

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_execution_request(
        result
    )

    return result


def save_paper_execution_request(
    result: PaperExecutionRequestResult,
) -> tuple[Path, Path]:
    """
    V9.7 결과를 JSON으로 저장합니다.
    """

    PAPER_EXECUTION_REQUEST_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_EXECUTION_REQUEST_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "paper_execution_request_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PAPER_EXECUTION_REQUEST_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "paper_execution_request_latest.json"
        )
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(
        report_path,
        payload,
    )

    write_json_file(
        latest_path,
        payload,
    )

    return (
        report_path,
        latest_path,
    )


def print_paper_execution_request(
    result: PaperExecutionRequestResult,
) -> None:
    """
    V9.7 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.7 "
        "PAPER EXECUTION REQUEST BUILDER"
    )
    print("=" * 140)

    print(
        f"Request status                 : "
        f"{result.request_status}"
    )

    print(
        f"Request status label           : "
        f"{result.request_status_label}"
    )

    print(
        f"Request action                 : "
        f"{result.request_action}"
    )

    print(
        f"Request action label           : "
        f"{result.request_action_label}"
    )

    print(
        f"Request ID                     : "
        f"{result.request_id}"
    )

    print(
        f"Idempotency key                : "
        f"{result.idempotency_key}"
    )

    print()
    print("APPROVAL")
    print("-" * 140)

    print(
        f"Approval status                : "
        f"{result.approval_status}"
    )

    print(
        f"Approval request               : "
        f"{result.approval_request}"
    )

    print(
        f"Approval actor                 : "
        f"{result.approval_actor}"
    )

    print(
        f"Approved at                    : "
        f"{result.approved_at}"
    )

    print()
    print("PAPER ORDER REQUEST")
    print("-" * 140)

    print(
        f"Side                           : "
        f"{result.side}"
    )

    print(
        f"Quantity                       : "
        f"{result.quantity}"
    )

    print(
        f"Order type                     : "
        f"{result.order_type}"
    )

    print(
        f"Time in force                  : "
        f"{result.time_in_force}"
    )

    print(
        f"Reference price                : "
        f"${result.reference_price:,.2f}"
    )

    print(
        f"Requested price                : "
        f"{result.requested_price}"
    )

    print(
        f"Estimated order value          : "
        f"${result.estimated_order_value:,.2f}"
    )

    print()
    print("PAPER EXECUTION")
    print("-" * 140)

    print(
        f"Paper execution authorized     : "
        f"{result.paper_execution_authorized}"
    )

    print(
        f"Paper execution requested      : "
        f"{result.paper_execution_requested}"
    )

    print(
        f"Paper execution pending        : "
        f"{result.paper_execution_pending}"
    )

    print(
        f"Paper fill created             : "
        f"{result.paper_fill_created}"
    )

    print()
    print("LIVE EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Live execution authorized      : "
        f"{result.live_execution_authorized}"
    )

    print(
        f"Broker order created           : "
        f"{result.broker_order_created}"
    )

    print(
        f"Live order created             : "
        f"{result.live_order_created}"
    )

    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
    )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Source loaded                  : "
        f"{result.source_loaded}"
    )

    print(
        f"Source valid                   : "
        f"{result.source_valid}"
    )

    print(
        f"Approval checks passed         : "
        f"{result.approval_checks_passed}"
    )

    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )

    print(
        f"Order checks passed            : "
        f"{result.order_checks_passed}"
    )

    print(
        f"Request generated              : "
        f"{result.request_generated}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 140)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * 140)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * 140)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Manual Approval file    : "
        f"{result.source_manual_approval_file}"
    )

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 140)

    print(
        "주의: 이 모듈은 Paper Broker로 전달할 가상 주문 "
        "요청서만 생성합니다. 가상 체결, 실제 주문 또는 "
        "Broker API 호출은 수행하지 않습니다."
    )