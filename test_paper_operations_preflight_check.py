import io
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from backtest.paper_operations_preflight_check import (
    REQUIRED_PREFLIGHT_TEXT,
    PaperOperationsPreflightPolicy,
    load_latest_paper_operations_preflight,
    run_paper_operations_preflight_check,
    save_paper_operations_preflight,
    validate_preflight_policy,
    verify_saved_preflight_payload,
)
from test_approved_paper_operations_handoff import (
    create_approve_source,
    create_handoff,
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def next_weekday() -> str:
    value = date.today()
    while value.weekday() >= 5:
        value += timedelta(days=1)
    return value.isoformat()


def create_handoff_source() -> Any:
    return create_handoff(create_approve_source())


def run_preflight(
    source: Any,
    *,
    trading_date: Any = None,
    market_status: Any = "PAPER_OPEN",
    operator: Any = None,
    symbols: Any = ("AAPL", "MSFT", "NVDA"),
    cash_balance: Any = 10000.0,
    data_age: Any = 5,
    confirmation: Any = REQUIRED_PREFLIGHT_TEXT,
) -> Any:
    return run_silently(
        run_paper_operations_preflight_check,
        source,
        trading_date or next_weekday(),
        market_status,
        operator or source.handoff_operator,
        symbols,
        cash_balance,
        data_age,
        confirmation,
    )


def assert_safety(result: Any) -> None:
    if result.paper_execution_authorized:
        raise RuntimeError(
            "Paper Execution이 허용되었습니다."
        )
    if result.automatic_execution_authorized:
        raise RuntimeError(
            "자동 실행이 허용되었습니다."
        )
    if not result.execution_blocked:
        raise RuntimeError(
            "Execution이 차단되지 않았습니다."
        )
    if (
        result.broker_api_called
        or result.broker_order_created
        or result.live_order_created
        or result.live_execution_authorized
    ):
        raise RuntimeError(
            "Broker 또는 Live 실행 안전값이 위반되었습니다."
        )


def validate_ready(source: Any) -> Any:
    result = run_preflight(source)
    if result.version != "V12.6":
        raise RuntimeError(
            "Preflight Version이 V12.6이 아닙니다."
        )
    if result.preflight_status != "READY":
        raise RuntimeError(
            "정상 Preflight가 READY가 아닙니다."
        )
    if result.total_item_count != 12:
        raise RuntimeError(
            "Preflight Item 수가 12개가 아닙니다."
        )
    if result.passed_item_count != 12:
        raise RuntimeError(
            "12개 Preflight Item이 모두 통과하지 않았습니다."
        )
    if not result.paper_preflight_authorized:
        raise RuntimeError(
            "Paper Preflight가 허용되지 않았습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Preflight의 All Checks가 실패했습니다."
        )
    assert_safety(result)
    return result


def validate_blocked(
    source: Any,
    name: str,
    **changes: Any,
) -> Any:
    result = run_preflight(source, **changes)
    if result.preflight_status != "BLOCKED":
        raise RuntimeError(
            f"{name} 조건이 BLOCKED로 차단되지 않았습니다."
        )
    if result.paper_preflight_authorized:
        raise RuntimeError(
            f"{name} 조건에서 Preflight가 허용되었습니다."
        )
    assert_safety(result)
    return result


def validate_tampered_source(source: Any) -> Any:
    record = replace(
        source.handoff_records[-1],
        handoff_note="변경된 Handoff 메모",
    )
    tampered = replace(
        source,
        handoff_records=(record,),
    )
    result = run_preflight(tampered)
    if result.preflight_status != "FAILED":
        raise RuntimeError(
            "변경된 Handoff Hash가 FAILED로 차단되지 않았습니다."
        )
    if result.handoff_chain_checks_passed:
        raise RuntimeError(
            "변경된 Handoff가 Chain 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_unsafe_source(source: Any) -> Any:
    unsafe = replace(
        source,
        broker_api_called=True,
        execution_blocked=False,
    )
    result = run_preflight(unsafe)
    if result.preflight_status != "FAILED":
        raise RuntimeError(
            "위험한 Source가 FAILED로 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Source가 Safety 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_invalid_input(source: Any) -> Any:
    result = run_preflight(
        source,
        trading_date="2026-99-99",
    )
    if result.preflight_status != "FAILED":
        raise RuntimeError(
            "잘못된 날짜가 FAILED로 처리되지 않았습니다."
        )
    if result.input_checks_passed:
        raise RuntimeError(
            "잘못된 날짜가 Input 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_policy() -> None:
    policy = PaperOperationsPreflightPolicy()
    valid, errors = validate_preflight_policy(policy)
    if not valid or errors:
        raise RuntimeError(
            "기본 Preflight Policy가 유효하지 않습니다."
        )
    try:
        policy.maximum_data_age_minutes = 1
        raise RuntimeError(
            "Preflight Policy가 변경되었습니다."
        )
    except FrozenInstanceError:
        pass
    invalid = replace(
        policy,
        broker_execution_disabled=False,
    )
    valid, errors = validate_preflight_policy(invalid)
    if valid or not errors:
        raise RuntimeError(
            "위험한 Preflight Policy가 차단되지 않았습니다."
        )


def validate_save_load(result: Any) -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        save_paper_operations_preflight(
            result,
            directory,
        )
        loaded = load_latest_paper_operations_preflight(
            directory
        )
        valid, errors = verify_saved_preflight_payload(
            loaded
        )
        if not valid or errors:
            raise RuntimeError(
                "저장된 Preflight 검증에 실패했습니다."
            )


def print_checks(
    ready: Any,
    weekend: Any,
    market_closed: Any,
    duplicates: Any,
    low_cash: Any,
    stale_data: Any,
    wrong_operator: Any,
    wrong_text: Any,
    tampered: Any,
    unsafe: Any,
    invalid: Any,
) -> None:
    checks = {
        "Version is V12.6": ready.version == "V12.6",
        "Default policy is valid": (
            ready.policy_checks_passed
        ),
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Twelve preflight items were created": (
            ready.total_item_count == 12
        ),
        "All preflight items passed": (
            ready.passed_item_count == 12
        ),
        "READY preflight was created": (
            ready.preflight_status == "READY"
        ),
        "Weekend was blocked": (
            weekend.preflight_status == "BLOCKED"
        ),
        "Closed paper market was blocked": (
            market_closed.preflight_status == "BLOCKED"
        ),
        "Duplicate symbols were blocked": (
            duplicates.preflight_status == "BLOCKED"
        ),
        "Low cash was blocked": (
            low_cash.preflight_status == "BLOCKED"
        ),
        "Stale data was blocked": (
            stale_data.preflight_status == "BLOCKED"
        ),
        "Wrong operator was blocked": (
            wrong_operator.preflight_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.preflight_status == "BLOCKED"
        ),
        "Handoff tampering failed": (
            tampered.preflight_status == "FAILED"
        ),
        "Unsafe source failed": (
            unsafe.preflight_status == "FAILED"
        ),
        "Invalid input failed": (
            invalid.preflight_status == "FAILED"
        ),
        "Result save and load passed": True,
        "Paper preflight was authorized": (
            ready.paper_preflight_authorized
        ),
        "Paper execution remains unauthorized": (
            not ready.paper_execution_authorized
        ),
        "Automatic execution remains disabled": (
            not ready.automatic_execution_authorized
        ),
        "Execution remains blocked": (
            ready.execution_blocked
        ),
        "Broker API was not called": (
            not ready.broker_api_called
        ),
        "Broker order was not created": (
            not ready.broker_order_created
        ),
        "Live order was not created": (
            not ready.live_order_created
        ),
        "Live execution not authorized": (
            not ready.live_execution_authorized
        ),
        "All checks passed": ready.all_checks_passed,
    }
    line = "=" * 100
    print()
    print(line)
    print(
        "AI STOCK BOT V12.6 PAPER OPERATIONS "
        "PREFLIGHT CHECK TEST"
    )
    print(line)
    print()
    print("V12.6 VALIDATION CHECKS")
    print("-" * 100)
    for name, value in checks.items():
        print(f"{name:<58} : {value}")
        if not value:
            raise RuntimeError(
                f"Validation Check 실패: {name}"
            )
    print(line)


def main() -> None:
    validate_policy()
    source = create_handoff_source()
    ready = validate_ready(source)
    saturday = date.today()
    while saturday.weekday() != 5:
        saturday += timedelta(days=1)
    weekend = validate_blocked(
        source,
        "Weekend",
        trading_date=saturday.isoformat(),
    )
    market_closed = validate_blocked(
        source,
        "Market Closed",
        market_status="PAPER_CLOSED",
    )
    duplicates = validate_blocked(
        source,
        "Duplicate Symbols",
        symbols=("AAPL", "AAPL"),
    )
    low_cash = validate_blocked(
        source,
        "Low Cash",
        cash_balance=50.0,
    )
    stale_data = validate_blocked(
        source,
        "Stale Data",
        data_age=30,
    )
    wrong_operator = validate_blocked(
        source,
        "Wrong Operator",
        operator="wrong-operator",
    )
    wrong_text = validate_blocked(
        source,
        "Wrong Confirmation",
        confirmation="CONFIRM",
    )
    tampered = validate_tampered_source(source)
    unsafe = validate_unsafe_source(source)
    invalid = validate_invalid_input(source)
    validate_save_load(ready)
    print_checks(
        ready,
        weekend,
        market_closed,
        duplicates,
        low_cash,
        stale_data,
        wrong_operator,
        wrong_text,
        tampered,
        unsafe,
        invalid,
    )
    print()
    print(
        "V12.6 paper operations preflight check "
        "test completed successfully."
    )
    print(
        "거래일, Paper Market, 종목, Cash, Data 신선도, "
        "Operator 및 Hash Chain이 검증되었습니다."
    )
    print(
        "Preflight 준비만 허용되며 Broker 주문과 Live "
        "Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
