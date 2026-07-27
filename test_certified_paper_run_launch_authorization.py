import io
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from backtest.certified_paper_run_launch_authorization import (
    REQUIRED_LAUNCH_TEXT,
    CertifiedPaperRunLaunchAuthorizationPolicy,
    authorize_certified_paper_run_launch,
    load_latest_certified_paper_run_launch_authorization,
    save_certified_paper_run_launch_authorization,
    validate_authorization_policy,
    verify_launch_authorization,
    verify_saved_authorization_payload,
)
from test_paper_run_readiness_certificate import (
    create_ready_source,
    issue,
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_certificate_source() -> Any:
    return issue(create_ready_source())


def authorize(
    source: Any,
    existing: Any = None,
    operator: Any = None,
    text: Any = REQUIRED_LAUNCH_TEXT,
) -> Any:
    return run_silently(
        authorize_certified_paper_run_launch,
        source,
        operator or source.certificates[-1].operator,
        text,
        existing,
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


def validate_authorized() -> tuple[Any, Any]:
    source = create_certificate_source()
    result = authorize(source)
    if result.version != "V12.8":
        raise RuntimeError(
            "Launch Authorization Version이 V12.8이 아닙니다."
        )
    if result.result_status != "AUTHORIZED":
        raise RuntimeError(
            "정상 Launch Authorization이 AUTHORIZED가 아닙니다."
        )
    if not result.paper_launch_authorized:
        raise RuntimeError(
            "Paper Launch가 허용되지 않았습니다."
        )
    if result.total_authorization_count != 1:
        raise RuntimeError(
            "첫 Authorization 수가 1이 아닙니다."
        )
    valid, time_valid, errors = (
        verify_launch_authorization(
            result.authorizations[0]
        )
    )
    if not valid or not time_valid or errors:
        raise RuntimeError(
            "발급된 Authorization 검증에 실패했습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "Launch Authorization All Checks가 실패했습니다."
        )
    assert_safety(result)
    return source, result


def validate_second(first: Any) -> Any:
    result = authorize(
        create_certificate_source(),
        first.authorizations,
    )
    if result.result_status != "AUTHORIZED":
        raise RuntimeError(
            "두 번째 Authorization 발급에 실패했습니다."
        )
    if result.total_authorization_count != 2:
        raise RuntimeError(
            "Authorization 수가 2가 아닙니다."
        )
    assert_safety(result)
    return result


def validate_blocked(
    source: Any,
    name: str,
    *,
    existing: Any = None,
    operator: Any = None,
    text: Any = REQUIRED_LAUNCH_TEXT,
) -> Any:
    result = authorize(
        source,
        existing,
        operator,
        text,
    )
    if result.result_status != "BLOCKED":
        raise RuntimeError(
            f"{name} 조건이 BLOCKED로 차단되지 않았습니다."
        )
    assert_safety(result)
    return result


def validate_expired_certificate(source: Any) -> Any:
    expired = replace(
        source.certificates[-1],
        expires_at=(
            datetime.now() - timedelta(minutes=1)
        ).isoformat(),
    )
    # expires_at 변경에 맞는 Hash를 만들지 않았으므로
    # 만료와 변조가 동시에 감지되어 FAILED가 되어야 합니다.
    changed = replace(
        source,
        certificates=(expired,),
    )
    result = authorize(changed)
    if result.result_status != "FAILED":
        raise RuntimeError(
            "만료된 Certificate가 FAILED로 차단되지 않았습니다."
        )
    assert_safety(result)
    return result


def validate_authorization_tampering(first: Any) -> Any:
    tampered = replace(
        first.authorizations[0],
        operator="changed-operator",
    )
    result = authorize(
        create_certificate_source(),
        (tampered,),
    )
    if result.result_status != "FAILED":
        raise RuntimeError(
            "변경된 Authorization이 FAILED로 차단되지 않았습니다."
        )
    if result.existing_authorization_checks_passed:
        raise RuntimeError(
            "변경된 Authorization이 Hash 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_unsafe_source(source: Any) -> Any:
    unsafe = replace(
        source,
        broker_api_called=True,
        execution_blocked=False,
    )
    result = authorize(unsafe)
    if result.result_status != "FAILED":
        raise RuntimeError(
            "위험한 Source가 FAILED로 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Source가 Safety 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_expiration(first: Any) -> None:
    item = first.authorizations[0]
    checked_at = (
        datetime.fromisoformat(item.expires_at)
        + timedelta(seconds=1)
    )
    valid, time_valid, errors = (
        verify_launch_authorization(
            item,
            checked_at,
        )
    )
    if valid or time_valid or not errors:
        raise RuntimeError(
            "만료된 Authorization이 차단되지 않았습니다."
        )


def validate_policy() -> None:
    policy = (
        CertifiedPaperRunLaunchAuthorizationPolicy()
    )
    valid, errors = validate_authorization_policy(
        policy
    )
    if not valid or errors:
        raise RuntimeError(
            "기본 Authorization Policy가 유효하지 않습니다."
        )
    try:
        policy.authorization_validity_minutes = 1
        raise RuntimeError(
            "Authorization Policy가 변경되었습니다."
        )
    except FrozenInstanceError:
        pass
    invalid = replace(
        policy,
        broker_execution_disabled=False,
    )
    valid, errors = validate_authorization_policy(
        invalid
    )
    if valid or not errors:
        raise RuntimeError(
            "위험한 Authorization Policy가 차단되지 않았습니다."
        )


def validate_save_load(result: Any) -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        save_certified_paper_run_launch_authorization(
            result,
            directory,
        )
        loaded = (
            load_latest_certified_paper_run_launch_authorization(
                directory
            )
        )
        valid, errors = verify_saved_authorization_payload(
            loaded
        )
        if not valid or errors:
            raise RuntimeError(
                "저장된 Authorization 검증에 실패했습니다."
            )


def print_checks(
    first: Any,
    second: Any,
    duplicate: Any,
    wrong_operator: Any,
    wrong_text: Any,
    expired_certificate: Any,
    tampered: Any,
    unsafe: Any,
) -> None:
    checks = {
        "Version is V12.8": first.version == "V12.8",
        "Default policy is valid": (
            first.policy_checks_passed
        ),
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Launch authorization was issued": (
            first.result_status == "AUTHORIZED"
        ),
        "Authorization hash passed": (
            first.issued_authorization_checks_passed
        ),
        "Second authorization was issued": (
            second.total_authorization_count == 2
        ),
        "Duplicate certificate was blocked": (
            duplicate.result_status == "BLOCKED"
        ),
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Expired certificate failed": (
            expired_certificate.result_status == "FAILED"
        ),
        "Authorization tampering failed": (
            tampered.result_status == "FAILED"
        ),
        "Expired authorization was blocked": True,
        "Unsafe source failed": (
            unsafe.result_status == "FAILED"
        ),
        "Result save and load passed": True,
        "Paper launch was authorized": (
            first.paper_launch_authorized
        ),
        "Paper execution remains unauthorized": (
            not first.paper_execution_authorized
        ),
        "Automatic execution remains disabled": (
            not first.automatic_execution_authorized
        ),
        "Execution remains blocked": (
            first.execution_blocked
        ),
        "Broker API was not called": (
            not first.broker_api_called
        ),
        "Broker order was not created": (
            not first.broker_order_created
        ),
        "Live order was not created": (
            not first.live_order_created
        ),
        "Live execution not authorized": (
            not first.live_execution_authorized
        ),
        "All checks passed": (
            first.all_checks_passed
            and second.all_checks_passed
        ),
    }
    line = "=" * 100
    print()
    print(line)
    print(
        "AI STOCK BOT V12.8 CERTIFIED PAPER RUN "
        "LAUNCH AUTHORIZATION TEST"
    )
    print(line)
    print()
    print("V12.8 VALIDATION CHECKS")
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
    source, first = validate_authorized()
    second = validate_second(first)
    duplicate = validate_blocked(
        source,
        "Duplicate",
        existing=first.authorizations,
    )
    wrong_operator = validate_blocked(
        source,
        "Wrong Operator",
        operator="wrong-operator",
    )
    wrong_text = validate_blocked(
        source,
        "Wrong Confirmation",
        text="AUTHORIZE",
    )
    expired_certificate = (
        validate_expired_certificate(source)
    )
    tampered = validate_authorization_tampering(first)
    validate_expiration(first)
    unsafe = validate_unsafe_source(source)
    validate_save_load(second)
    print_checks(
        first,
        second,
        duplicate,
        wrong_operator,
        wrong_text,
        expired_certificate,
        tampered,
        unsafe,
    )
    print()
    print(
        "V12.8 certified paper run launch authorization "
        "test completed successfully."
    )
    print(
        "유효 Certificate, 수동 Launch 허가, SHA-256 Hash, "
        "중복, 변조 및 만료 차단이 검증되었습니다."
    )
    print(
        "Paper Launch 준비만 허용되며 Broker 주문과 Live "
        "Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
