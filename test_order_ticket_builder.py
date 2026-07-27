import json
from dataclasses import asdict
from pathlib import Path

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

VALID_TICKET_STATUSES = {
    "WAITING_MANUAL_APPROVAL",
    "NO_ACTION",
    "BLOCKED",
}


def print_header() -> None:
    """
    V9.5 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 120)
    print("AI STOCK BOT V9.5 ORDER TICKET BUILDER TEST")
    print("=" * 120)


def print_check(
    name: str,
    value: bool,
) -> None:
    """
    검증 결과를 보기 좋게 출력합니다.
    """

    print(
        f"{name:<45}: {value}"
    )


def load_json_file(
    file_path: Path,
) -> dict:
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


def validate_position_sizing_result(
    sizing_result: PositionSizingResult,
) -> None:
    """
    V9.4 Position Sizing 결과가 V9.5에 전달 가능한지 검사합니다.
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

    if not sizing_result.execution_blocked:
        raise RuntimeError(
            "V9.4 Execution Blocked가 False입니다."
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


def validate_ticket_structure(
    ticket: OrderTicket,
) -> None:
    """
    V9.5 Order Ticket의 구조와 필수값을 검사합니다.
    """

    if not isinstance(
        ticket,
        OrderTicket,
    ):
        raise RuntimeError(
            "결과가 OrderTicket 형식이 아닙니다."
        )

    if ticket.version != "V9.5":
        raise RuntimeError(
            f"Order Ticket 버전이 V9.5가 아닙니다: "
            f"{ticket.version}"
        )

    if not ticket.symbol:
        raise RuntimeError(
            "Order Ticket Symbol이 비어 있습니다."
        )

    if ticket.symbol != ticket.symbol.upper():
        raise RuntimeError(
            "Order Ticket Symbol이 대문자가 아닙니다."
        )

    if ticket.side not in VALID_SIDES:
        raise RuntimeError(
            f"올바르지 않은 Side입니다: {ticket.side}"
        )

    if ticket.order_type not in VALID_ORDER_TYPES:
        raise RuntimeError(
            f"올바르지 않은 Order Type입니다: "
            f"{ticket.order_type}"
        )

    if ticket.time_in_force not in VALID_TIME_IN_FORCE:
        raise RuntimeError(
            f"올바르지 않은 Time In Force입니다: "
            f"{ticket.time_in_force}"
        )

    if ticket.status not in VALID_TICKET_STATUSES:
        raise RuntimeError(
            f"올바르지 않은 Ticket Status입니다: "
            f"{ticket.status}"
        )

    if not isinstance(
        ticket.quantity,
        int,
    ):
        raise RuntimeError(
            "Quantity가 int 형식이 아닙니다."
        )

    if ticket.quantity < 0:
        raise RuntimeError(
            "Quantity가 음수입니다."
        )

    if not isinstance(
        ticket.reference_price,
        float,
    ):
        raise RuntimeError(
            "Reference Price가 float 형식이 아닙니다."
        )

    if ticket.reference_price <= 0:
        raise RuntimeError(
            "Reference Price가 0 이하입니다."
        )

    if not isinstance(
        ticket.estimated_value,
        float,
    ):
        raise RuntimeError(
            "Estimated Value가 float 형식이 아닙니다."
        )

    if ticket.estimated_value < 0:
        raise RuntimeError(
            "Estimated Value가 음수입니다."
        )

    if not ticket.created_at:
        raise RuntimeError(
            "Created At이 비어 있습니다."
        )

    if not isinstance(
        ticket.reasons,
        list,
    ):
        raise RuntimeError(
            "Reasons가 List 형식이 아닙니다."
        )

    if not isinstance(
        ticket.warnings,
        list,
    ):
        raise RuntimeError(
            "Warnings가 List 형식이 아닙니다."
        )

    if not isinstance(
        ticket.next_actions,
        list,
    ):
        raise RuntimeError(
            "Next Actions가 List 형식이 아닙니다."
        )

    if not ticket.reasons:
        raise RuntimeError(
            "Reasons가 비어 있습니다."
        )

    if not ticket.warnings:
        raise RuntimeError(
            "Warnings가 비어 있습니다."
        )

    if not ticket.next_actions:
        raise RuntimeError(
            "Next Actions가 비어 있습니다."
        )


def validate_ticket_matches_sizing(
    ticket: OrderTicket,
    sizing_result: PositionSizingResult,
) -> None:
    """
    V9.5 Ticket이 V9.4 Position Sizing 결과와 일치하는지 검사합니다.
    """

    if ticket.symbol != sizing_result.symbol:
        raise RuntimeError(
            "Order Ticket Symbol이 Position Sizing 결과와 "
            "일치하지 않습니다."
        )

    expected_side = "NONE"

    if sizing_result.position_action == "ENTER_LONG":
        expected_side = "BUY"

    elif sizing_result.position_action == "EXIT_LONG":
        expected_side = "SELL"

    if ticket.side != expected_side:
        raise RuntimeError(
            "Order Ticket Side가 Position Action과 "
            "일치하지 않습니다. "
            f"Expected={expected_side}, "
            f"Actual={ticket.side}"
        )

    if ticket.quantity != sizing_result.proposed_shares:
        raise RuntimeError(
            "Order Ticket Quantity가 Position Sizing 수량과 "
            "일치하지 않습니다."
        )

    if abs(
        ticket.reference_price
        - sizing_result.latest_close
    ) > 0.0001:
        raise RuntimeError(
            "Order Ticket Reference Price가 Latest Close와 "
            "일치하지 않습니다."
        )

    expected_value = round(
        ticket.quantity
        * ticket.reference_price,
        2,
    )

    if abs(
        ticket.estimated_value
        - expected_value
    ) > 0.0001:
        raise RuntimeError(
            "Estimated Value 계산이 일치하지 않습니다."
        )

    if ticket.side == "BUY":
        if sizing_result.sizing_action != "PREPARE_ENTRY":
            raise RuntimeError(
                "BUY Ticket인데 Sizing Action이 "
                "PREPARE_ENTRY가 아닙니다."
            )

    if ticket.side == "SELL":
        if sizing_result.sizing_action != "PREPARE_EXIT":
            raise RuntimeError(
                "SELL Ticket인데 Sizing Action이 "
                "PREPARE_EXIT가 아닙니다."
            )


def validate_execution_safety(
    ticket: OrderTicket,
) -> None:
    """
    V9.5가 실제 주문을 생성하지 않았는지 검사합니다.
    """

    if not ticket.execution_blocked:
        raise RuntimeError(
            "Execution Blocked가 False입니다."
        )

    if not ticket.manual_approval_required:
        raise RuntimeError(
            "Manual Approval Required가 False입니다."
        )

    if ticket.broker_order_created:
        raise RuntimeError(
            "Broker Order가 생성되었습니다."
        )

    if ticket.paper_order_created:
        raise RuntimeError(
            "Paper Order가 생성되었습니다."
        )

    if ticket.live_order_created:
        raise RuntimeError(
            "Live Order가 생성되었습니다."
        )

    if ticket.status != "WAITING_MANUAL_APPROVAL":
        raise RuntimeError(
            "Order Ticket Status가 "
            "WAITING_MANUAL_APPROVAL이 아닙니다."
        )

    warning_text = " ".join(
        str(warning)
        for warning in ticket.warnings
    ).lower()

    if "broker" not in warning_text:
        raise RuntimeError(
            "Warnings에 Broker API 차단 설명이 없습니다."
        )

    if "paper" not in warning_text:
        raise RuntimeError(
            "Warnings에 Paper Trade 차단 설명이 없습니다."
        )

    if "live" not in warning_text:
        raise RuntimeError(
            "Warnings에 Live Trade 차단 설명이 없습니다."
        )


def validate_saved_files(
    ticket: OrderTicket,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    저장된 Report 및 Latest JSON 파일을 검사합니다.
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

    expected_payload = asdict(
        ticket
    )

    if report_payload != expected_payload:
        raise RuntimeError(
            "저장된 JSON 내용이 Order Ticket 결과와 "
            "일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "side",
        "quantity",
        "reference_price",
        "estimated_value",
        "order_type",
        "time_in_force",
        "status",
        "execution_blocked",
        "manual_approval_required",
        "broker_order_created",
        "paper_order_created",
        "live_order_created",
        "created_at",
        "reasons",
        "warnings",
        "next_actions",
    }

    missing_keys = (
        required_keys
        - set(report_payload.keys())
    )

    if missing_keys:
        raise RuntimeError(
            "저장된 Order Ticket JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )


def validate_manual_ticket_calculation() -> None:
    """
    OrderTicket Dataclass의 직접 계산 예제를 검사합니다.
    """

    ticket = OrderTicket(
        version="V9.5",
        symbol="TEST",
        side="BUY",
        quantity=5,
        reference_price=100.0,
        estimated_value=500.0,
        order_type="MARKET",
        time_in_force="DAY",
        status="WAITING_MANUAL_APPROVAL",
        execution_blocked=True,
        manual_approval_required=True,
        broker_order_created=False,
        paper_order_created=False,
        live_order_created=False,
        created_at="2026-01-01T00:00:00",
        reasons=[
            "Test reason",
        ],
        warnings=[
            "No broker API called.",
            "No paper trade created.",
            "No live trade created.",
        ],
        next_actions=[
            "Review order.",
        ],
    )

    validate_ticket_structure(
        ticket
    )

    if ticket.quantity * ticket.reference_price != (
        ticket.estimated_value
    ):
        raise RuntimeError(
            "Manual Ticket Estimated Value 계산이 틀렸습니다."
        )


def print_ticket_result(
    ticket: OrderTicket,
    sizing_result: PositionSizingResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.5 최종 결과를 출력합니다.
    """

    print()
    print("=" * 120)
    print("V9.5 ORDER TICKET BUILDER RESULT")
    print("=" * 120)

    print(
        f"Symbol                         : "
        f"{ticket.symbol}"
    )

    print(
        f"Side                           : "
        f"{ticket.side}"
    )

    print(
        f"Quantity                       : "
        f"{ticket.quantity}"
    )

    print(
        f"Reference price                : "
        f"${ticket.reference_price:,.2f}"
    )

    print(
        f"Estimated value                : "
        f"${ticket.estimated_value:,.2f}"
    )

    print(
        f"Order type                     : "
        f"{ticket.order_type}"
    )

    print(
        f"Time in force                  : "
        f"{ticket.time_in_force}"
    )

    print(
        f"Ticket status                  : "
        f"{ticket.status}"
    )

    print()
    print("SOURCE POSITION SIZING")
    print("-" * 120)

    print(
        f"Sizing action                  : "
        f"{sizing_result.sizing_action}"
    )

    print(
        f"Position action                : "
        f"{sizing_result.position_action}"
    )

    print(
        f"Risk decision                  : "
        f"{sizing_result.risk_decision}"
    )

    print(
        f"Approved position percent      : "
        f"{sizing_result.approved_position_percent:.2f}%"
    )

    print(
        f"Proposed shares                : "
        f"{sizing_result.proposed_shares}"
    )

    print(
        f"Proposed position value        : "
        f"${sizing_result.proposed_position_value:,.2f}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 120)

    print(
        f"Execution blocked              : "
        f"{ticket.execution_blocked}"
    )

    print(
        f"Manual approval required       : "
        f"{ticket.manual_approval_required}"
    )

    print(
        f"Broker order created           : "
        f"{ticket.broker_order_created}"
    )

    print(
        f"Paper order created            : "
        f"{ticket.paper_order_created}"
    )

    print(
        f"Live order created             : "
        f"{ticket.live_order_created}"
    )

    print()
    print("FILES")
    print("-" * 120)

    print(
        f"Position sizing source         : "
        f"{sizing_result.latest_path}"
    )

    print(
        f"Report file                    : "
        f"{report_path}"
    )

    print(
        f"Latest file                    : "
        f"{latest_path}"
    )

    print("=" * 120)


def print_validation_checks(
    ticket: OrderTicket,
    sizing_result: PositionSizingResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True/False로 출력합니다.
    """

    expected_side = "NONE"

    if sizing_result.position_action == "ENTER_LONG":
        expected_side = "BUY"

    elif sizing_result.position_action == "EXIT_LONG":
        expected_side = "SELL"

    expected_value = round(
        ticket.quantity
        * ticket.reference_price,
        2,
    )

    checks = {
        "Version is V9.5": (
            ticket.version == "V9.5"
        ),
        "Symbol matches sizing": (
            ticket.symbol == sizing_result.symbol
        ),
        "Side is valid": (
            ticket.side in VALID_SIDES
        ),
        "Side matches action": (
            ticket.side == expected_side
        ),
        "Quantity is valid": (
            isinstance(
                ticket.quantity,
                int,
            )
            and ticket.quantity >= 0
        ),
        "Quantity matches sizing": (
            ticket.quantity
            == sizing_result.proposed_shares
        ),
        "Reference price is valid": (
            ticket.reference_price > 0
        ),
        "Reference price matches": (
            abs(
                ticket.reference_price
                - sizing_result.latest_close
            )
            <= 0.0001
        ),
        "Estimated value is valid": (
            ticket.estimated_value >= 0
        ),
        "Estimated value matches": (
            abs(
                ticket.estimated_value
                - expected_value
            )
            <= 0.0001
        ),
        "Order type is valid": (
            ticket.order_type
            in VALID_ORDER_TYPES
        ),
        "Time in force is valid": (
            ticket.time_in_force
            in VALID_TIME_IN_FORCE
        ),
        "Status is approval waiting": (
            ticket.status
            == "WAITING_MANUAL_APPROVAL"
        ),
        "Execution is blocked": (
            ticket.execution_blocked
        ),
        "Manual approval required": (
            ticket.manual_approval_required
        ),
        "Broker order not created": (
            not ticket.broker_order_created
        ),
        "Paper order not created": (
            not ticket.paper_order_created
        ),
        "Live order not created": (
            not ticket.live_order_created
        ),
        "Reasons exist": bool(
            ticket.reasons
        ),
        "Warnings exist": bool(
            ticket.warnings
        ),
        "Next actions exist": bool(
            ticket.next_actions
        ),
        "Position sizing passed": (
            sizing_result.all_checks_passed
        ),
        "Position sizing blocked execution": (
            sizing_result.execution_blocked
        ),
        "Report file exists": (
            report_path.exists()
        ),
        "Latest file exists": (
            latest_path.exists()
        ),
    }

    print()
    print("=" * 120)
    print("VALIDATION CHECKS")
    print("=" * 120)

    for name, value in checks.items():
        print_check(
            name,
            value,
        )

    print("=" * 120)

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
    V9.5 Order Ticket Builder 통합 테스트입니다.
    """

    symbol = "AAPL"
    account_cash = 10_000.0

    print_header()

    try:
        sizing_result = (
            run_position_sizing_manager(
                symbol=symbol,
                account_cash=account_cash,
            )
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

        validate_ticket_structure(
            ticket
        )

        validate_ticket_matches_sizing(
            ticket=ticket,
            sizing_result=sizing_result,
        )

        validate_execution_safety(
            ticket
        )

        validate_manual_ticket_calculation()

        (
            report_path,
            latest_path,
        ) = save_order_ticket(
            ticket
        )

        validate_saved_files(
            ticket=ticket,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_ticket_result(
            ticket=ticket,
            sizing_result=sizing_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_validation_checks(
            ticket=ticket,
            sizing_result=sizing_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V9.5 order ticket builder "
            "test completed successfully."
        )

        print(
            f"Position Action은 "
            f"{sizing_result.position_action}이고 "
            f"Order Ticket Side는 "
            f"{ticket.side}입니다."
        )

        print(
            f"검토용 수량은 "
            f"{ticket.quantity}주이며 "
            f"예상 금액은 "
            f"${ticket.estimated_value:,.2f}입니다."
        )

        print(
            f"Ticket Status는 "
            f"{ticket.status}입니다."
        )

        print(
            "실제 Broker Order, Paper Order, Live Order는 "
            "모두 생성되지 않았습니다."
        )

        print(
            "주의: 이 결과는 승인 대기용 연구 티켓이며 "
            "실제 증권 주문이 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 120)
        print("TEST CANCELLED")
        print("=" * 120)

        print(
            "사용자가 V9.5 Order Ticket Builder "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 120)
        print("V9.5 ORDER TICKET BUILDER ERROR")
        print("=" * 120)

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