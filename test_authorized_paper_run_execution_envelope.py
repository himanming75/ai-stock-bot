import io
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from backtest.authorized_paper_run_execution_envelope import (
    REQUIRED_ENVELOPE_TEXT,
    AuthorizedPaperRunExecutionEnvelopePolicy,
    build_authorized_paper_run_execution_envelope,
    load_latest_authorized_paper_run_execution_envelope,
    save_authorized_paper_run_execution_envelope,
    validate_envelope_policy,
    verify_execution_envelope,
    verify_saved_envelope_payload,
)
from test_certified_paper_run_launch_authorization import (
    authorize,
    create_certificate_source,
)


VALID_ORDERS = (
    {
        "order_id": "paper-order-001",
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "LIMIT",
        "quantity": 10,
        "limit_price": 200.0,
    },
    {
        "order_id": "paper-order-002",
        "symbol": "MSFT",
        "side": "SELL",
        "order_type": "MARKET",
        "quantity": 5,
        "limit_price": None,
        "reference_price": 450.0,
    },
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_authorization_source() -> Any:
    return authorize(create_certificate_source())


def build(
    source: Any,
    orders: Any = VALID_ORDERS,
    operator: Any = None,
    text: Any = REQUIRED_ENVELOPE_TEXT,
) -> Any:
    return run_silently(
        build_authorized_paper_run_execution_envelope,
        source,
        orders,
        operator or source.authorizations[-1].operator,
        text,
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
            "Broker 또는 Live 안전값이 위반되었습니다."
        )


def validate_sealed() -> tuple[Any, Any]:
    source = create_authorization_source()
    result = build(source)
    if result.version != "V12.9":
        raise RuntimeError(
            "Envelope Version이 V12.9가 아닙니다."
        )
    if result.result_status != "SEALED":
        raise RuntimeError(
            "정상 Envelope가 SEALED가 아닙니다."
        )
    if result.order_count != 2:
        raise RuntimeError(
            "Envelope Order 수가 2가 아닙니다."
        )
    if not result.paper_envelope_authorized:
        raise RuntimeError(
            "Paper Envelope가 허용되지 않았습니다."
        )
    valid, time_valid, errors = (
        verify_execution_envelope(result.envelope)
    )
    if not valid or not time_valid or errors:
        raise RuntimeError(
            "봉인된 Envelope 검증에 실패했습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "Envelope All Checks가 실패했습니다."
        )
    assert_safety(result)
    return source, result


def validate_blocked(
    source: Any,
    name: str,
    *,
    orders: Any = VALID_ORDERS,
    operator: Any = None,
    text: Any = REQUIRED_ENVELOPE_TEXT,
) -> Any:
    result = build(
        source,
        orders,
        operator,
        text,
    )
    if result.result_status != "BLOCKED":
        raise RuntimeError(
            f"{name} 조건이 BLOCKED로 차단되지 않았습니다."
        )
    assert_safety(result)
    return result


def validate_source_tampering(source: Any) -> Any:
    authorization = replace(
        source.authorizations[-1],
        operator="changed-operator",
    )
    changed = replace(
        source,
        authorizations=(authorization,),
    )
    result = build(
        changed,
        operator="changed-operator",
    )
    if result.result_status != "FAILED":
        raise RuntimeError(
            "변경된 Authorization이 FAILED로 차단되지 않았습니다."
        )
    assert_safety(result)
    return result


def validate_envelope_tampering(sealed: Any) -> None:
    tampered = replace(
        sealed.envelope,
        total_estimated_notional=1.0,
    )
    valid, _, errors = verify_execution_envelope(
        tampered
    )
    if valid or not errors:
        raise RuntimeError(
            "변경된 Envelope Hash가 차단되지 않았습니다."
        )


def validate_expiration(sealed: Any) -> None:
    checked_at = (
        datetime.fromisoformat(
            sealed.envelope.expires_at
        )
        + timedelta(seconds=1)
    )
    valid, time_valid, errors = (
        verify_execution_envelope(
            sealed.envelope,
            checked_at,
        )
    )
    if valid or time_valid or not errors:
        raise RuntimeError(
            "만료된 Envelope가 차단되지 않았습니다."
        )


def validate_unsafe_source(source: Any) -> Any:
    unsafe = replace(
        source,
        broker_api_called=True,
        execution_blocked=False,
    )
    result = build(unsafe)
    if result.result_status != "FAILED":
        raise RuntimeError(
            "위험한 Source가 FAILED로 차단되지 않았습니다."
        )
    assert_safety(result)
    return result


def validate_policy() -> None:
    policy = AuthorizedPaperRunExecutionEnvelopePolicy()
    valid, errors = validate_envelope_policy(policy)
    if not valid or errors:
        raise RuntimeError(
            "기본 Envelope Policy가 유효하지 않습니다."
        )
    try:
        policy.maximum_order_count = 1
        raise RuntimeError(
            "Envelope Policy가 변경되었습니다."
        )
    except FrozenInstanceError:
        pass
    invalid = replace(
        policy,
        broker_execution_disabled=False,
    )
    valid, errors = validate_envelope_policy(invalid)
    if valid or not errors:
        raise RuntimeError(
            "위험한 Envelope Policy가 차단되지 않았습니다."
        )


def validate_save_load(result: Any) -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        save_authorized_paper_run_execution_envelope(
            result,
            directory,
        )
        loaded = (
            load_latest_authorized_paper_run_execution_envelope(
                directory
            )
        )
        valid, errors = verify_saved_envelope_payload(
            loaded
        )
        if not valid or errors:
            raise RuntimeError(
                "저장된 Envelope 검증에 실패했습니다."
            )


def print_checks(
    sealed: Any,
    wrong_operator: Any,
    wrong_text: Any,
    duplicate_ids: Any,
    bad_symbol: Any,
    bad_quantity: Any,
    bad_price: Any,
    source_tampered: Any,
    unsafe: Any,
) -> None:
    checks = {
        "Version is V12.9": sealed.version == "V12.9",
        "Default policy is valid": (
            sealed.policy_checks_passed
        ),
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Execution envelope was sealed": (
            sealed.result_status == "SEALED"
        ),
        "Two paper orders were sealed": (
            sealed.order_count == 2
        ),
        "Envelope hash passed": (
            sealed.envelope_hash_checks_passed
        ),
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Duplicate order IDs were blocked": (
            duplicate_ids.result_status == "BLOCKED"
        ),
        "Unauthorized symbol was blocked": (
            bad_symbol.result_status == "BLOCKED"
        ),
        "Invalid quantity was blocked": (
            bad_quantity.result_status == "BLOCKED"
        ),
        "Invalid price was blocked": (
            bad_price.result_status == "BLOCKED"
        ),
        "Authorization tampering failed": (
            source_tampered.result_status == "FAILED"
        ),
        "Envelope tampering was blocked": True,
        "Expired envelope was blocked": True,
        "Unsafe source failed": (
            unsafe.result_status == "FAILED"
        ),
        "Result save and load passed": True,
        "Paper envelope was authorized": (
            sealed.paper_envelope_authorized
        ),
        "Paper execution remains unauthorized": (
            not sealed.paper_execution_authorized
        ),
        "Automatic execution remains disabled": (
            not sealed.automatic_execution_authorized
        ),
        "Execution remains blocked": (
            sealed.execution_blocked
        ),
        "Broker API was not called": (
            not sealed.broker_api_called
        ),
        "Broker order was not created": (
            not sealed.broker_order_created
        ),
        "Live order was not created": (
            not sealed.live_order_created
        ),
        "Live execution not authorized": (
            not sealed.live_execution_authorized
        ),
        "All checks passed": sealed.all_checks_passed,
    }
    line = "=" * 100
    print()
    print(line)
    print(
        "AI STOCK BOT V12.9 AUTHORIZED PAPER RUN "
        "EXECUTION ENVELOPE TEST"
    )
    print(line)
    print()
    print("V12.9 VALIDATION CHECKS")
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
    source, sealed = validate_sealed()
    wrong_operator = validate_blocked(
        source,
        "Wrong Operator",
        operator="wrong-operator",
    )
    wrong_text = validate_blocked(
        source,
        "Wrong Confirmation",
        text="BUILD ENVELOPE",
    )
    duplicate_orders = (
        VALID_ORDERS[0],
        {
            **VALID_ORDERS[1],
            "order_id": "paper-order-001",
        },
    )
    duplicate_ids = validate_blocked(
        source,
        "Duplicate IDs",
        orders=duplicate_orders,
    )
    bad_symbol = validate_blocked(
        source,
        "Bad Symbol",
        orders=(
            {
                **VALID_ORDERS[0],
                "symbol": "TSLA",
            },
        ),
    )
    bad_quantity = validate_blocked(
        source,
        "Bad Quantity",
        orders=(
            {
                **VALID_ORDERS[0],
                "quantity": 0,
            },
        ),
    )
    bad_price = validate_blocked(
        source,
        "Bad Price",
        orders=(
            {
                **VALID_ORDERS[0],
                "limit_price": -1.0,
            },
        ),
    )
    source_tampered = validate_source_tampering(
        source
    )
    validate_envelope_tampering(sealed)
    validate_expiration(sealed)
    unsafe = validate_unsafe_source(source)
    validate_save_load(sealed)
    print_checks(
        sealed,
        wrong_operator,
        wrong_text,
        duplicate_ids,
        bad_symbol,
        bad_quantity,
        bad_price,
        source_tampered,
        unsafe,
    )
    print()
    print(
        "V12.9 authorized paper run execution envelope "
        "test completed successfully."
    )
    print(
        "Launch Authorization, Paper Orders, SHA-256 Envelope, "
        "입력, 변조 및 만료 차단이 검증되었습니다."
    )
    print(
        "실행 봉투만 생성되며 Broker API와 Live "
        "Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
