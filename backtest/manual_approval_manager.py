import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

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

MANUAL_APPROVAL_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "manual_approval"
)


VALID_APPROVAL_REQUESTS = {
    "WAIT",
    "APPROVE_PAPER",
    "REJECT",
}


VALID_APPROVAL_STATUSES = {
    "WAITING_APPROVAL",
    "APPROVED_FOR_PAPER",
    "REJECTED",
    "EXPIRED",
    "BLOCKED",
    "FAILED",
}


VALID_TICKET_SIDES = {
    "BUY",
    "SELL",
    "NONE",
}


VALID_TICKET_STATUSES = {
    "WAITING_MANUAL_APPROVAL",
    "NO_ACTION",
    "BLOCKED",
}


@dataclass(frozen=True)
class ApprovalPolicy:
    """
    V9.6 수동 승인 정책입니다.

    실제 증권 주문 권한이 아니라
    연구용 Paper Trading 승인 기록 정책입니다.
    """

    approval_expiration_minutes: int = 60

    minimum_quantity: int = 1
    maximum_quantity: int = 100_000

    minimum_estimated_value: float = 25.0
    maximum_estimated_value: float = 1_000_000.0

    allow_buy: bool = True
    allow_sell: bool = True
    allow_market_order: bool = True

    paper_only: bool = True
    require_manual_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ManualApprovalResult:
    """
    V9.6 Manual Approval Manager 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_order_ticket_file: str | None

    approval_status: str
    approval_status_label: str
    approval_request: str

    approved: bool
    rejected: bool
    expired: bool
    blocked: bool

    ticket_version: str
    ticket_status: str
    ticket_side: str
    quantity: int

    reference_price: float
    estimated_value: float

    order_type: str
    time_in_force: str

    ticket_created_at: str
    expires_at: str
    minutes_until_expiration: float

    approval_actor: str
    approval_note: str | None
    approved_at: str | None
    rejected_at: str | None

    paper_execution_allowed: bool
    live_execution_allowed: bool

    source_loaded: bool
    source_valid: bool
    ticket_checks_passed: bool
    expiration_checks_passed: bool
    policy_checks_passed: bool
    decision_generated: bool
    all_checks_passed: bool

    order_generated: bool
    broker_order_generated: bool
    paper_order_generated: bool
    live_order_generated: bool

    execution_blocked: bool
    manual_approval_required: bool

    approval_policy: ApprovalPolicy

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["approval_policy"] = (
            self.approval_policy.to_dict()
        )

        return payload


def normalize_symbol(
    symbol: str,
) -> str:
    """
    Symbol을 대문자로 정규화합니다.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일을 이용해 안전하게 저장합니다.
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

    temporary_path.replace(
        file_path
    )


def is_valid_number(
    value: Any,
) -> bool:
    """
    값이 유효한 숫자인지 검사합니다.
    """

    if isinstance(
        value,
        bool,
    ):
        return False

    try:
        numeric_value = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    return math.isfinite(
        numeric_value
    )


def parse_datetime(
    value: str,
) -> datetime:
    """
    ISO 형식 문자열을 datetime으로 변환합니다.
    """

    if not value:
        raise ValueError(
            "Datetime 문자열이 비어 있습니다."
        )

    try:
        return datetime.fromisoformat(
            value
        )

    except ValueError as error:
        raise ValueError(
            f"올바르지 않은 Datetime 형식입니다: {value}"
        ) from error


def validate_approval_policy(
    policy: ApprovalPolicy,
) -> tuple[
    bool,
    list[str],
]:
    """
    ApprovalPolicy 설정값을 검사합니다.
    """

    errors: list[str] = []

    if not (
        1
        <= policy.approval_expiration_minutes
        <= 10_080
    ):
        errors.append(
            "Approval Expiration Minutes가 "
            "허용 범위를 벗어났습니다."
        )

    if not (
        1
        <= policy.minimum_quantity
        <= policy.maximum_quantity
    ):
        errors.append(
            "Minimum Quantity와 Maximum Quantity가 "
            "올바르지 않습니다."
        )

    if not (
        0.0
        < policy.minimum_estimated_value
        <= policy.maximum_estimated_value
    ):
        errors.append(
            "Minimum Estimated Value와 Maximum Estimated Value가 "
            "올바르지 않습니다."
        )

    boolean_fields = {
        "allow_buy": policy.allow_buy,
        "allow_sell": policy.allow_sell,
        "allow_market_order": policy.allow_market_order,
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
            errors.append(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if not policy.paper_only:
        errors.append(
            "V9.6에서는 Paper Only가 반드시 True여야 합니다."
        )

    if not policy.require_manual_approval:
        errors.append(
            "V9.6에서는 Require Manual Approval이 "
            "반드시 True여야 합니다."
        )

    return (
        not errors,
        errors,
    )


def validate_order_ticket(
    ticket: OrderTicket,
) -> tuple[
    bool,
    list[str],
]:
    """
    V9.5 Order Ticket을 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        ticket,
        OrderTicket,
    ):
        errors.append(
            "Order Ticket 형식이 올바르지 않습니다."
        )

        return (
            False,
            errors,
        )

    if ticket.version != "V9.5":
        errors.append(
            "Order Ticket 버전이 V9.5가 아닙니다."
        )

    if not ticket.symbol:
        errors.append(
            "Order Ticket Symbol이 비어 있습니다."
        )

    if ticket.side not in VALID_TICKET_SIDES:
        errors.append(
            f"올바르지 않은 Ticket Side입니다: {ticket.side}"
        )

    if ticket.status not in VALID_TICKET_STATUSES:
        errors.append(
            f"올바르지 않은 Ticket Status입니다: "
            f"{ticket.status}"
        )

    if not isinstance(
        ticket.quantity,
        int,
    ):
        errors.append(
            "Ticket Quantity가 int 형식이 아닙니다."
        )

    elif ticket.quantity < 0:
        errors.append(
            "Ticket Quantity가 음수입니다."
        )

    if not is_valid_number(
        ticket.reference_price
    ):
        errors.append(
            "Reference Price가 유효한 숫자가 아닙니다."
        )

    elif float(
        ticket.reference_price
    ) <= 0:
        errors.append(
            "Reference Price가 0 이하입니다."
        )

    if not is_valid_number(
        ticket.estimated_value
    ):
        errors.append(
            "Estimated Value가 유효한 숫자가 아닙니다."
        )

    elif float(
        ticket.estimated_value
    ) < 0:
        errors.append(
            "Estimated Value가 음수입니다."
        )

    expected_value = round(
        int(ticket.quantity)
        * float(ticket.reference_price),
        2,
    )

    if abs(
        float(ticket.estimated_value)
        - expected_value
    ) > 0.01:
        errors.append(
            "Estimated Value가 Quantity × Reference Price와 "
            "일치하지 않습니다."
        )

    try:
        parse_datetime(
            ticket.created_at
        )

    except ValueError as error:
        errors.append(
            str(error)
        )

    if not ticket.execution_blocked:
        errors.append(
            "V9.5 Ticket에서 Execution이 차단되지 않았습니다."
        )

    if not ticket.manual_approval_required:
        errors.append(
            "V9.5 Ticket에서 Manual Approval Required가 "
            "False입니다."
        )

    if ticket.broker_order_created:
        errors.append(
            "V9.5 Ticket에서 Broker Order가 생성되었습니다."
        )

    if ticket.paper_order_created:
        errors.append(
            "V9.5 Ticket에서 Paper Order가 생성되었습니다."
        )

    if ticket.live_order_created:
        errors.append(
            "V9.5 Ticket에서 Live Order가 생성되었습니다."
        )

    return (
        not errors,
        errors,
    )


def validate_ticket_against_policy(
    ticket: OrderTicket,
    policy: ApprovalPolicy,
) -> tuple[
    bool,
    list[str],
]:
    """
    주문 티켓이 승인 정책에 맞는지 검사합니다.
    """

    errors: list[str] = []

    if ticket.side == "BUY":
        if not policy.allow_buy:
            errors.append(
                "Approval Policy에서 BUY가 허용되지 않습니다."
            )

    elif ticket.side == "SELL":
        if not policy.allow_sell:
            errors.append(
                "Approval Policy에서 SELL이 허용되지 않습니다."
            )

    elif ticket.side == "NONE":
        errors.append(
            "Side가 NONE인 티켓은 승인할 수 없습니다."
        )

    if ticket.order_type == "MARKET":
        if not policy.allow_market_order:
            errors.append(
                "Approval Policy에서 Market Order가 "
                "허용되지 않습니다."
            )

    if not (
        policy.minimum_quantity
        <= ticket.quantity
        <= policy.maximum_quantity
    ):
        errors.append(
            "Ticket Quantity가 승인 정책 범위를 벗어났습니다."
        )

    if not (
        policy.minimum_estimated_value
        <= ticket.estimated_value
        <= policy.maximum_estimated_value
    ):
        errors.append(
            "Estimated Value가 승인 정책 범위를 벗어났습니다."
        )

    if ticket.status != "WAITING_MANUAL_APPROVAL":
        errors.append(
            "Ticket Status가 WAITING_MANUAL_APPROVAL이 아닙니다."
        )

    return (
        not errors,
        errors,
    )


def calculate_expiration(
    ticket_created_at: str,
    expiration_minutes: int,
    current_time: datetime,
) -> tuple[
    datetime,
    float,
    bool,
]:
    """
    승인 만료시간과 남은 시간을 계산합니다.
    """

    created_datetime = parse_datetime(
        ticket_created_at
    )

    expires_at = (
        created_datetime
        + timedelta(
            minutes=expiration_minutes
        )
    )

    remaining_seconds = (
        expires_at
        - current_time
    ).total_seconds()

    minutes_until_expiration = (
        remaining_seconds
        / 60.0
    )

    expired = (
        current_time
        >= expires_at
    )

    return (
        expires_at,
        minutes_until_expiration,
        expired,
    )


def determine_approval_decision(
    approval_request: str,
    ticket_valid: bool,
    policy_valid: bool,
    expiration_valid: bool,
    expired: bool,
) -> tuple[
    str,
    str,
    bool,
    bool,
    bool,
    bool,
    list[str],
]:
    """
    수동 승인 요청을 최종 승인 상태로 변환합니다.
    """

    if not (
        ticket_valid
        and policy_valid
        and expiration_valid
    ):
        return (
            "BLOCKED",
            "승인 검사 실패로 차단",
            False,
            False,
            False,
            True,
            [
                "필수 승인 검사가 통과되지 않았습니다.",
                "티켓을 Paper Trading 단계로 전달하지 않습니다.",
            ],
        )

    if expired:
        return (
            "EXPIRED",
            "승인 유효시간 만료",
            False,
            False,
            True,
            False,
            [
                "주문 티켓의 승인 유효시간이 만료되었습니다.",
                "새로운 시장 데이터로 티켓을 다시 생성해야 합니다.",
            ],
        )

    if approval_request == "APPROVE_PAPER":
        return (
            "APPROVED_FOR_PAPER",
            "Paper Trading 승인 완료",
            True,
            False,
            False,
            False,
            [
                "사용자가 Paper Trading용 티켓을 승인했습니다.",
                "실거래 주문 권한은 부여되지 않았습니다.",
            ],
        )

    if approval_request == "REJECT":
        return (
            "REJECTED",
            "사용자 승인 거절",
            False,
            True,
            False,
            False,
            [
                "사용자가 주문 티켓을 거절했습니다.",
                "Paper Trading 단계로 전달하지 않습니다.",
            ],
        )

    return (
        "WAITING_APPROVAL",
        "사용자 승인 대기",
        False,
        False,
        False,
        False,
        [
            "주문 티켓이 수동 승인을 기다리고 있습니다.",
            "승인 또는 거절 전까지 실행 단계로 진행하지 않습니다.",
        ],
    )


def build_approval_notes(
    approval_status: str,
    approval_actor: str,
    ticket_errors: list[str],
    policy_errors: list[str],
) -> tuple[
    list[str],
    list[str],
]:
    """
    경고와 다음 작업 목록을 생성합니다.
    """

    warnings: list[str] = []

    warnings.extend(
        ticket_errors
    )

    warnings.extend(
        policy_errors
    )

    warnings.extend(
        [
            (
                "이 승인 기록은 Paper Trading 연구용이며 "
                "실제 증권 주문 승인이 아닙니다."
            ),
            (
                "V9.6은 Broker API, 실제 계좌 또는 "
                "주문 전송 기능을 호출하지 않습니다."
            ),
            (
                "Live Execution은 승인 상태와 관계없이 "
                "계속 차단됩니다."
            ),
            (
                f"승인 기록자 표시는 {approval_actor}이며 "
                "인증된 전자서명을 의미하지 않습니다."
            ),
        ]
    )

    if approval_status == "APPROVED_FOR_PAPER":
        next_actions = [
            (
                "승인된 티켓을 V9.7 Paper Execution "
                "Request Builder에 전달합니다."
            ),
            (
                "Paper Broker가 가상 체결 전에 "
                "현금과 보유 수량을 다시 검사합니다."
            ),
            (
                "실거래 주문 모듈에는 전달하지 않습니다."
            ),
        ]

    elif approval_status == "REJECTED":
        next_actions = [
            (
                "현재 주문 티켓을 종료 처리합니다."
            ),
            (
                "필요하면 새로운 시장 데이터로 "
                "분석을 다시 실행합니다."
            ),
            (
                "Paper 또는 Live 주문을 생성하지 않습니다."
            ),
        ]

    elif approval_status == "EXPIRED":
        next_actions = [
            (
                "만료된 티켓을 사용하지 않습니다."
            ),
            (
                "최신 가격과 신호를 이용해 "
                "V9.1부터 다시 계산합니다."
            ),
            (
                "새로운 티켓에 대해 다시 수동 승인합니다."
            ),
        ]

    elif approval_status == "BLOCKED":
        next_actions = [
            (
                "승인 처리를 중단합니다."
            ),
            (
                "Ticket 또는 Approval Policy 오류를 수정합니다."
            ),
            (
                "검사가 통과되기 전 실행 단계로 전달하지 않습니다."
            ),
        ]

    else:
        next_actions = [
            (
                "사용자가 APPROVE_PAPER 또는 REJECT를 "
                "선택할 때까지 기다립니다."
            ),
            (
                "승인 대기 중 가격이나 신호가 바뀌면 "
                "티켓을 다시 생성합니다."
            ),
            (
                "대기 중에는 어떠한 주문도 생성하지 않습니다."
            ),
        ]

    return (
        warnings,
        next_actions,
    )


def run_manual_approval_manager(
    symbol: str = "AAPL",
    ticket: OrderTicket | None = None,
    sizing_result: PositionSizingResult | None = None,
    approval_request: str = "WAIT",
    approval_actor: str = "MANUAL_USER",
    approval_note: str | None = None,
    approval_policy: ApprovalPolicy | None = None,
    account_cash: float = 10_000.0,
    current_time: datetime | None = None,
) -> ManualApprovalResult:
    """
    V9.5 Order Ticket에 대한 수동 승인 상태를 기록합니다.

    approval_request 값:

    WAIT
    APPROVE_PAPER
    REJECT

    실제 주문은 생성하거나 실행하지 않습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    normalized_request = (
        approval_request
        .strip()
        .upper()
    )

    if normalized_request not in VALID_APPROVAL_REQUESTS:
        raise ValueError(
            "approval_request는 WAIT, APPROVE_PAPER, "
            "REJECT 중 하나여야 합니다."
        )

    normalized_actor = (
        approval_actor.strip()
        or "MANUAL_USER"
    )

    policy = (
        approval_policy
        if approval_policy is not None
        else ApprovalPolicy()
    )

    (
        policy_valid,
        policy_errors,
    ) = validate_approval_policy(
        policy
    )

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

        save_order_ticket(
            ticket
        )

    if ticket.symbol != normalized_symbol:
        raise ValueError(
            "Order Ticket Symbol과 요청 Symbol이 "
            "일치하지 않습니다."
        )

    (
        ticket_valid,
        ticket_errors,
    ) = validate_order_ticket(
        ticket
    )

    (
        ticket_policy_valid,
        ticket_policy_errors,
    ) = validate_ticket_against_policy(
        ticket=ticket,
        policy=policy,
    )

    policy_errors.extend(
        ticket_policy_errors
    )

    policy_checks_passed = (
        policy_valid
        and ticket_policy_valid
    )

    now = (
        current_time
        if current_time is not None
        else datetime.now()
    )

    expiration_checks_passed = True

    try:
        (
            expires_at,
            minutes_until_expiration,
            expired,
        ) = calculate_expiration(
            ticket_created_at=ticket.created_at,
            expiration_minutes=(
                policy.approval_expiration_minutes
            ),
            current_time=now,
        )

    except ValueError as error:
        expiration_checks_passed = False

        expires_at = now
        minutes_until_expiration = 0.0
        expired = False

        ticket_errors.append(
            str(error)
        )

    (
        approval_status,
        approval_status_label,
        approved,
        rejected,
        expired_decision,
        blocked,
        decision_reasons,
    ) = determine_approval_decision(
        approval_request=normalized_request,
        ticket_valid=ticket_valid,
        policy_valid=policy_checks_passed,
        expiration_valid=(
            expiration_checks_passed
        ),
        expired=expired,
    )

    expired = (
        expired
        or expired_decision
    )

    approved_at: str | None = None
    rejected_at: str | None = None

    if approved:
        approved_at = now.isoformat()

    if rejected:
        rejected_at = now.isoformat()

    decision_generated = (
        approval_status
        in VALID_APPROVAL_STATUSES
    )

    paper_execution_allowed = (
        approval_status
        == "APPROVED_FOR_PAPER"
        and approved
        and not expired
        and not blocked
        and policy.paper_only
    )

    live_execution_allowed = False

    all_checks_passed = (
        ticket_valid
        and policy_checks_passed
        and expiration_checks_passed
        and decision_generated
    )

    reasons: list[str] = []

    reasons.extend(
        decision_reasons
    )

    reasons.extend(
        [
            (
                f"티켓 Side는 {ticket.side}입니다."
            ),
            (
                f"티켓 수량은 {ticket.quantity}주입니다."
            ),
            (
                f"예상 티켓 금액은 "
                f"${ticket.estimated_value:,.2f}입니다."
            ),
            (
                f"승인 요청은 {normalized_request}입니다."
            ),
        ]
    )

    (
        warnings,
        next_actions,
    ) = build_approval_notes(
        approval_status=approval_status,
        approval_actor=normalized_actor,
        ticket_errors=ticket_errors,
        policy_errors=policy_errors,
    )

    source_file: str | None = None

    if sizing_result is not None:
        source_file = (
            sizing_result.latest_path
            or sizing_result.report_path
        )

    result = ManualApprovalResult(
        version="V9.6",
        symbol=normalized_symbol,
        created_at=now.isoformat(),

        source_order_ticket_file=(
            source_file
        ),

        approval_status=approval_status,
        approval_status_label=(
            approval_status_label
        ),
        approval_request=normalized_request,

        approved=approved,
        rejected=rejected,
        expired=expired,
        blocked=blocked,

        ticket_version=ticket.version,
        ticket_status=ticket.status,
        ticket_side=ticket.side,
        quantity=int(
            ticket.quantity
        ),

        reference_price=float(
            ticket.reference_price
        ),
        estimated_value=float(
            ticket.estimated_value
        ),

        order_type=ticket.order_type,
        time_in_force=ticket.time_in_force,

        ticket_created_at=(
            ticket.created_at
        ),
        expires_at=(
            expires_at.isoformat()
        ),
        minutes_until_expiration=float(
            minutes_until_expiration
        ),

        approval_actor=normalized_actor,
        approval_note=approval_note,
        approved_at=approved_at,
        rejected_at=rejected_at,

        paper_execution_allowed=(
            paper_execution_allowed
        ),
        live_execution_allowed=(
            live_execution_allowed
        ),

        source_loaded=True,
        source_valid=ticket_valid,
        ticket_checks_passed=(
            ticket_valid
        ),
        expiration_checks_passed=(
            expiration_checks_passed
        ),
        policy_checks_passed=(
            policy_checks_passed
        ),
        decision_generated=(
            decision_generated
        ),
        all_checks_passed=(
            all_checks_passed
        ),

        order_generated=False,
        broker_order_generated=False,
        paper_order_generated=False,
        live_order_generated=False,

        execution_blocked=True,
        manual_approval_required=(
            approval_status
            == "WAITING_APPROVAL"
        ),

        approval_policy=policy,

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_manual_approval_manager(
        result
    )

    return result


def save_manual_approval_manager(
    result: ManualApprovalResult,
) -> tuple[
    Path,
    Path,
]:
    """
    V9.6 승인 결과를 JSON으로 저장합니다.
    """

    MANUAL_APPROVAL_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        MANUAL_APPROVAL_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "manual_approval_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        MANUAL_APPROVAL_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "manual_approval_latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

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


def print_manual_approval_manager(
    result: ManualApprovalResult,
) -> None:
    """
    V9.6 Manual Approval 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.6 "
        "MANUAL APPROVAL MANAGER"
    )
    print("=" * 140)

    print(
        f"Approval status                : "
        f"{result.approval_status}"
    )

    print(
        f"Approval status label          : "
        f"{result.approval_status_label}"
    )

    print(
        f"Approval request               : "
        f"{result.approval_request}"
    )

    print(
        f"Approval actor                 : "
        f"{result.approval_actor}"
    )

    print()
    print("APPROVAL DECISION")
    print("-" * 140)

    print(
        f"Approved                       : "
        f"{result.approved}"
    )

    print(
        f"Rejected                       : "
        f"{result.rejected}"
    )

    print(
        f"Expired                        : "
        f"{result.expired}"
    )

    print(
        f"Blocked                        : "
        f"{result.blocked}"
    )

    print(
        f"Paper execution allowed        : "
        f"{result.paper_execution_allowed}"
    )

    print(
        f"Live execution allowed         : "
        f"{result.live_execution_allowed}"
    )

    print()
    print("ORDER TICKET")
    print("-" * 140)

    print(
        f"Ticket version                 : "
        f"{result.ticket_version}"
    )

    print(
        f"Ticket status                  : "
        f"{result.ticket_status}"
    )

    print(
        f"Side                           : "
        f"{result.ticket_side}"
    )

    print(
        f"Quantity                       : "
        f"{result.quantity}"
    )

    print(
        f"Reference price                : "
        f"${result.reference_price:,.2f}"
    )

    print(
        f"Estimated value                : "
        f"${result.estimated_value:,.2f}"
    )

    print(
        f"Order type                     : "
        f"{result.order_type}"
    )

    print(
        f"Time in force                  : "
        f"{result.time_in_force}"
    )

    print()
    print("EXPIRATION")
    print("-" * 140)

    print(
        f"Ticket created at              : "
        f"{result.ticket_created_at}"
    )

    print(
        f"Expires at                     : "
        f"{result.expires_at}"
    )

    print(
        f"Minutes until expiration       : "
        f"{result.minutes_until_expiration:.2f}"
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
        f"Ticket checks passed           : "
        f"{result.ticket_checks_passed}"
    )

    print(
        f"Expiration checks passed       : "
        f"{result.expiration_checks_passed}"
    )

    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )

    print(
        f"Decision generated             : "
        f"{result.decision_generated}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Order generated                : "
        f"{result.order_generated}"
    )

    print(
        f"Broker order generated         : "
        f"{result.broker_order_generated}"
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
        f"Source Order Ticket file       : "
        f"{result.source_order_ticket_file}"
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
        "주의: 이 모듈은 Paper Trading 승인 상태만 기록하며 "
        "실제 주문, Broker 주문, 모의 체결 또는 실거래 주문을 "
        "생성하거나 전송하지 않습니다."
    )