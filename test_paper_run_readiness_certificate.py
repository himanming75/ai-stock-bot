import io
import uuid
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from backtest.paper_run_readiness_certificate import (
    REQUIRED_CERTIFICATE_TEXT,
    PaperRunReadinessCertificatePolicy,
    issue_paper_run_readiness_certificate,
    load_latest_paper_run_readiness_certificate,
    save_paper_run_readiness_certificate,
    validate_certificate_policy,
    verify_readiness_certificate,
    verify_saved_certificate_payload,
)
from test_paper_operations_preflight_check import (
    create_handoff_source,
    validate_ready,
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_ready_source() -> Any:
    return validate_ready(create_handoff_source())


def issue(
    source: Any,
    existing: Any = None,
    operator: Any = None,
    text: Any = REQUIRED_CERTIFICATE_TEXT,
) -> Any:
    return run_silently(
        issue_paper_run_readiness_certificate,
        source,
        operator or source.operator,
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


def validate_issued() -> tuple[Any, Any]:
    source = create_ready_source()
    result = issue(source)
    if result.version != "V12.7":
        raise RuntimeError(
            "Certificate Version이 V12.7이 아닙니다."
        )
    if result.issue_status != "ISSUED":
        raise RuntimeError(
            "정상 Certificate가 ISSUED가 아닙니다."
        )
    if result.total_certificate_count != 1:
        raise RuntimeError(
            "첫 Certificate 수가 1이 아닙니다."
        )
    if result.valid_certificate_count != 1:
        raise RuntimeError(
            "Valid Certificate 수가 1이 아닙니다."
        )
    if not result.paper_readiness_certified:
        raise RuntimeError(
            "Paper Readiness가 인증되지 않았습니다."
        )
    valid, time_valid, errors = (
        verify_readiness_certificate(
            result.certificates[0]
        )
    )
    if not valid or not time_valid or errors:
        raise RuntimeError(
            "발급된 Certificate 검증에 실패했습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "Certificate All Checks가 실패했습니다."
        )
    assert_safety(result)
    return source, result


def validate_second(first_result: Any) -> Any:
    source = create_ready_source()
    result = issue(
        source,
        first_result.certificates,
    )
    if result.issue_status != "ISSUED":
        raise RuntimeError(
            "두 번째 Certificate 발급에 실패했습니다."
        )
    if result.total_certificate_count != 2:
        raise RuntimeError(
            "Certificate 수가 2가 아닙니다."
        )
    assert_safety(result)
    return result


def validate_duplicate(
    source: Any,
    first_result: Any,
) -> Any:
    result = issue(
        source,
        first_result.certificates,
    )
    if result.issue_status != "BLOCKED":
        raise RuntimeError(
            "중복 Certificate가 BLOCKED로 차단되지 않았습니다."
        )
    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 Certificate가 Duplicate 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_wrong_operator(source: Any) -> Any:
    result = issue(
        source,
        operator="wrong-operator",
    )
    if result.issue_status != "BLOCKED":
        raise RuntimeError(
            "잘못된 Operator가 BLOCKED로 차단되지 않았습니다."
        )
    assert_safety(result)
    return result


def validate_wrong_text(source: Any) -> Any:
    result = issue(
        source,
        text="ISSUE CERTIFICATE",
    )
    if result.issue_status != "BLOCKED":
        raise RuntimeError(
            "잘못된 확인 문구가 BLOCKED로 차단되지 않았습니다."
        )
    assert_safety(result)
    return result


def validate_source_tampering(source: Any) -> Any:
    tampered = replace(
        source,
        passed_item_count=11,
    )
    result = issue(tampered)
    if result.issue_status != "FAILED":
        raise RuntimeError(
            "변경된 Preflight가 FAILED로 차단되지 않았습니다."
        )
    if result.source_checks_passed:
        raise RuntimeError(
            "변경된 Preflight가 Source 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_certificate_tampering(
    first_result: Any,
) -> Any:
    tampered = replace(
        first_result.certificates[0],
        cash_balance=1.0,
    )
    result = issue(
        create_ready_source(),
        (tampered,),
    )
    if result.issue_status != "FAILED":
        raise RuntimeError(
            "변경된 Certificate가 FAILED로 차단되지 않았습니다."
        )
    if result.existing_certificate_checks_passed:
        raise RuntimeError(
            "변경된 Certificate가 Hash 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_expiration(first_result: Any) -> None:
    certificate = first_result.certificates[0]
    checked_at = (
        datetime.fromisoformat(certificate.expires_at)
        + timedelta(seconds=1)
    )
    valid, time_valid, errors = (
        verify_readiness_certificate(
            certificate,
            checked_at,
        )
    )
    if valid or time_valid or not errors:
        raise RuntimeError(
            "만료된 Certificate가 차단되지 않았습니다."
        )


def validate_unsafe_source(source: Any) -> Any:
    unsafe = replace(
        source,
        broker_api_called=True,
        execution_blocked=False,
    )
    result = issue(unsafe)
    if result.issue_status != "FAILED":
        raise RuntimeError(
            "위험한 Source가 FAILED로 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Source가 Safety 검사를 통과했습니다."
        )
    assert_safety(result)
    return result


def validate_policy() -> None:
    policy = PaperRunReadinessCertificatePolicy()
    valid, errors = validate_certificate_policy(policy)
    if not valid or errors:
        raise RuntimeError(
            "기본 Certificate Policy가 유효하지 않습니다."
        )
    try:
        policy.validity_minutes = 1
        raise RuntimeError(
            "Certificate Policy가 변경되었습니다."
        )
    except FrozenInstanceError:
        pass
    invalid = replace(
        policy,
        broker_execution_disabled=False,
    )
    valid, errors = validate_certificate_policy(invalid)
    if valid or not errors:
        raise RuntimeError(
            "위험한 Certificate Policy가 차단되지 않았습니다."
        )


def validate_save_load(result: Any) -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        save_paper_run_readiness_certificate(
            result,
            directory,
        )
        loaded = (
            load_latest_paper_run_readiness_certificate(
                directory
            )
        )
        valid, errors = verify_saved_certificate_payload(
            loaded
        )
        if not valid or errors:
            raise RuntimeError(
                "저장된 Certificate 검증에 실패했습니다."
            )


def print_checks(
    issued: Any,
    second: Any,
    duplicate: Any,
    wrong_operator: Any,
    wrong_text: Any,
    source_tampered: Any,
    certificate_tampered: Any,
    unsafe: Any,
) -> None:
    checks = {
        "Version is V12.7": issued.version == "V12.7",
        "Default policy is valid": (
            issued.policy_checks_passed
        ),
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Readiness certificate was issued": (
            issued.issue_status == "ISSUED"
        ),
        "Certificate hash passed": (
            issued.issued_certificate_checks_passed
        ),
        "Second certificate was issued": (
            second.total_certificate_count == 2
        ),
        "Duplicate preflight was blocked": (
            duplicate.issue_status == "BLOCKED"
        ),
        "Wrong operator was blocked": (
            wrong_operator.issue_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.issue_status == "BLOCKED"
        ),
        "Source tampering failed": (
            source_tampered.issue_status == "FAILED"
        ),
        "Certificate tampering failed": (
            certificate_tampered.issue_status == "FAILED"
        ),
        "Expired certificate was blocked": True,
        "Unsafe source failed": (
            unsafe.issue_status == "FAILED"
        ),
        "Result save and load passed": True,
        "Paper readiness was certified": (
            issued.paper_readiness_certified
        ),
        "Paper execution remains unauthorized": (
            not issued.paper_execution_authorized
        ),
        "Automatic execution remains disabled": (
            not issued.automatic_execution_authorized
        ),
        "Execution remains blocked": (
            issued.execution_blocked
        ),
        "Broker API was not called": (
            not issued.broker_api_called
        ),
        "Broker order was not created": (
            not issued.broker_order_created
        ),
        "Live order was not created": (
            not issued.live_order_created
        ),
        "Live execution not authorized": (
            not issued.live_execution_authorized
        ),
        "All checks passed": (
            issued.all_checks_passed
            and second.all_checks_passed
        ),
    }
    line = "=" * 100
    print()
    print(line)
    print(
        "AI STOCK BOT V12.7 PAPER RUN READINESS "
        "CERTIFICATE TEST"
    )
    print(line)
    print()
    print("V12.7 VALIDATION CHECKS")
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
    source, issued = validate_issued()
    second = validate_second(issued)
    duplicate = validate_duplicate(source, issued)
    wrong_operator = validate_wrong_operator(source)
    wrong_text = validate_wrong_text(source)
    source_tampered = validate_source_tampering(source)
    certificate_tampered = (
        validate_certificate_tampering(issued)
    )
    validate_expiration(issued)
    unsafe = validate_unsafe_source(source)
    validate_save_load(second)
    print_checks(
        issued,
        second,
        duplicate,
        wrong_operator,
        wrong_text,
        source_tampered,
        certificate_tampered,
        unsafe,
    )
    print()
    print(
        "V12.7 paper run readiness certificate "
        "test completed successfully."
    )
    print(
        "READY Preflight 봉인, SHA-256 Certificate, 중복, "
        "변조 및 만료 차단이 검증되었습니다."
    )
    print(
        "Certificate는 준비 증명이며 Broker 주문과 Live "
        "Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
