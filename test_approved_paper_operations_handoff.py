import io
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from backtest.approved_paper_operations_handoff import (
    GENESIS_HANDOFF_HASH,
    REQUIRED_HANDOFF_TEXT,
    ApprovedPaperOperationsHandoffPolicy,
    handoff_approved_paper_operations,
    load_latest_approved_paper_operations_handoff,
    save_approved_paper_operations_handoff,
    validate_handoff_policy,
    verify_handoff_record_chain,
    verify_saved_handoff_payload,
)
from test_paper_trading_manual_review_decision import (
    APPROVE_REASON,
    HOLD_REASON,
    REJECT_REASON,
    REVIEWER,
    create_queue_with_two_items,
    record_decision,
    validate_approve,
)


HANDOFF_NOTE = "승인된 Paper 운영 준비 자료를 직접 확인하고 전달합니다."


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_approve_source() -> Any:
    queue_result = create_queue_with_two_items()
    return validate_approve(queue_result)


def assert_execution_safety(result: Any) -> None:
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
            "Execution 차단 상태가 아닙니다."
        )
    if result.broker_api_called:
        raise RuntimeError(
            "Broker API가 호출되었습니다."
        )
    if result.broker_order_created:
        raise RuntimeError(
            "Broker 주문이 생성되었습니다."
        )
    if result.live_order_created:
        raise RuntimeError(
            "Live 주문이 생성되었습니다."
        )
    if result.live_execution_authorized:
        raise RuntimeError(
            "Live Execution이 허용되었습니다."
        )


def create_handoff(
    decision_result: Any,
    existing_records: Any = None,
) -> Any:
    return run_silently(
        handoff_approved_paper_operations,
        decision_result,
        REVIEWER,
        HANDOFF_NOTE,
        REQUIRED_HANDOFF_TEXT,
        existing_records,
    )


def validate_success() -> tuple[Any, Any]:
    decision_result = create_approve_source()
    result = create_handoff(decision_result)
    if result.version != "V12.5":
        raise RuntimeError(
            "Approved Handoff Version이 V12.5가 아닙니다."
        )
    if result.handoff_status != "HANDED_OFF":
        raise RuntimeError(
            "APPROVE Source가 HANDED_OFF가 아닙니다."
        )
    if not result.paper_preparation_authorized:
        raise RuntimeError(
            "Paper Preparation이 허용되지 않았습니다."
        )
    if result.total_handoff_count != 1:
        raise RuntimeError(
            "첫 Handoff Record 수가 1이 아닙니다."
        )
    if (
        result.handoff_records[0].previous_hash
        != GENESIS_HANDOFF_HASH
    ):
        raise RuntimeError(
            "첫 Handoff가 Genesis Hash에 연결되지 않았습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Handoff의 All Checks가 실패했습니다."
        )
    assert_execution_safety(result)
    return decision_result, result


def validate_second_handoff(first_result: Any) -> Any:
    new_source = create_approve_source()
    result = create_handoff(
        new_source,
        first_result.handoff_records,
    )
    if result.handoff_status != "HANDED_OFF":
        raise RuntimeError(
            "두 번째 Handoff가 실패했습니다."
        )
    if result.total_handoff_count != 2:
        raise RuntimeError(
            "Handoff Record 수가 2가 아닙니다."
        )
    valid, errors = verify_handoff_record_chain(
        result.handoff_records
    )
    if not valid or errors:
        raise RuntimeError(
            "Handoff Hash Chain 검사가 실패했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_non_approve_blocked(
    decision: str,
    reason: str,
) -> Any:
    queue_result = create_queue_with_two_items()
    source = record_decision(
        queue_result,
        0,
        decision,
        reason,
    )
    result = create_handoff(source)
    if result.handoff_status != "BLOCKED":
        raise RuntimeError(
            f"{decision} Source가 BLOCKED로 차단되지 않았습니다."
        )
    if result.approval_checks_passed:
        raise RuntimeError(
            f"{decision} Source가 Approval 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_wrong_operator_blocked(
    source: Any,
) -> Any:
    result = run_silently(
        handoff_approved_paper_operations,
        source,
        "wrong-operator",
        HANDOFF_NOTE,
        REQUIRED_HANDOFF_TEXT,
    )
    if result.handoff_status != "BLOCKED":
        raise RuntimeError(
            "잘못된 Operator가 BLOCKED로 차단되지 않았습니다."
        )
    assert_execution_safety(result)
    return result


def validate_wrong_text_blocked(source: Any) -> Any:
    result = run_silently(
        handoff_approved_paper_operations,
        source,
        REVIEWER,
        HANDOFF_NOTE,
        "HANDOFF",
    )
    if result.handoff_status != "BLOCKED":
        raise RuntimeError(
            "잘못된 확인 문구가 BLOCKED로 차단되지 않았습니다."
        )
    assert_execution_safety(result)
    return result


def validate_duplicate_blocked(
    source: Any,
    first_result: Any,
) -> Any:
    result = create_handoff(
        source,
        first_result.handoff_records,
    )
    if result.handoff_status != "BLOCKED":
        raise RuntimeError(
            "중복 Handoff가 BLOCKED로 차단되지 않았습니다."
        )
    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 Handoff가 Duplicate 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_source_tampering_failed(source: Any) -> Any:
    tampered_record = replace(
        source.decision_records[-1],
        decision="HOLD",
    )
    tampered_source = replace(
        source,
        decision_records=(tampered_record,),
    )
    result = create_handoff(tampered_source)
    if result.handoff_status != "FAILED":
        raise RuntimeError(
            "변경된 Decision Hash가 FAILED로 차단되지 않았습니다."
        )
    if result.decision_chain_checks_passed:
        raise RuntimeError(
            "변경된 Decision이 Hash 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_handoff_tampering_failed(
    first_result: Any,
) -> Any:
    tampered = replace(
        first_result.handoff_records[0],
        handoff_note="변경된 메모",
    )
    result = create_handoff(
        create_approve_source(),
        (tampered,),
    )
    if result.handoff_status != "FAILED":
        raise RuntimeError(
            "변경된 Handoff Hash가 FAILED로 차단되지 않았습니다."
        )
    if result.existing_chain_checks_passed:
        raise RuntimeError(
            "변경된 Handoff가 Hash 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_unsafe_source_failed(source: Any) -> Any:
    unsafe = replace(
        source,
        broker_api_called=True,
        execution_blocked=False,
    )
    result = create_handoff(unsafe)
    if result.handoff_status != "FAILED":
        raise RuntimeError(
            "위험한 Source가 FAILED로 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Source가 Safety 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_policy() -> None:
    policy = ApprovedPaperOperationsHandoffPolicy()
    valid, errors = validate_handoff_policy(policy)
    if not valid or errors:
        raise RuntimeError(
            "기본 Handoff Policy가 유효하지 않습니다."
        )
    try:
        policy.minimum_note_length = 1
        raise RuntimeError(
            "Handoff Policy가 변경되었습니다."
        )
    except FrozenInstanceError:
        pass
    invalid = replace(
        policy,
        broker_execution_disabled=False,
    )
    valid, errors = validate_handoff_policy(invalid)
    if valid or not errors:
        raise RuntimeError(
            "위험한 Handoff Policy가 차단되지 않았습니다."
        )


def validate_save_and_load(result: Any) -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        saved = save_approved_paper_operations_handoff(
            result,
            directory,
        )
        if not saved.report_path or not saved.latest_path:
            raise RuntimeError(
                "Handoff 저장 경로가 없습니다."
            )
        loaded = (
            load_latest_approved_paper_operations_handoff(
                directory
            )
        )
        valid, errors = verify_saved_handoff_payload(
            loaded
        )
        if not valid or errors:
            raise RuntimeError(
                "저장된 Handoff 검증에 실패했습니다."
            )


def print_checks(
    success: Any,
    second: Any,
    rejected: Any,
    held: Any,
    wrong_operator: Any,
    wrong_text: Any,
    duplicate: Any,
    source_tampered: Any,
    handoff_tampered: Any,
    unsafe: Any,
) -> None:
    checks = {
        "Version is V12.5": success.version == "V12.5",
        "Default policy is valid": (
            success.policy_checks_passed
        ),
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "APPROVE source was handed off": (
            success.handoff_status == "HANDED_OFF"
        ),
        "Second handoff was recorded": (
            second.total_handoff_count == 2
        ),
        "Handoff hash chain passed": (
            second.updated_chain_checks_passed
        ),
        "REJECT source was blocked": (
            rejected.handoff_status == "BLOCKED"
        ),
        "HOLD source was blocked": (
            held.handoff_status == "BLOCKED"
        ),
        "Wrong operator was blocked": (
            wrong_operator.handoff_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.handoff_status == "BLOCKED"
        ),
        "Duplicate handoff was blocked": (
            duplicate.handoff_status == "BLOCKED"
        ),
        "Decision tampering failed": (
            source_tampered.handoff_status == "FAILED"
        ),
        "Handoff tampering failed": (
            handoff_tampered.handoff_status == "FAILED"
        ),
        "Unsafe source failed": (
            unsafe.handoff_status == "FAILED"
        ),
        "Result save and load passed": True,
        "Paper preparation was authorized": (
            success.paper_preparation_authorized
        ),
        "Paper execution remains unauthorized": (
            not success.paper_execution_authorized
        ),
        "Automatic execution remains disabled": (
            not success.automatic_execution_authorized
        ),
        "Execution remains blocked": (
            success.execution_blocked
        ),
        "Broker API was not called": (
            not success.broker_api_called
        ),
        "Broker order was not created": (
            not success.broker_order_created
        ),
        "Live order was not created": (
            not success.live_order_created
        ),
        "Live execution not authorized": (
            not success.live_execution_authorized
        ),
        "All checks passed": (
            success.all_checks_passed
            and second.all_checks_passed
        ),
    }
    line = "=" * 100
    print()
    print(line)
    print(
        "AI STOCK BOT V12.5 APPROVED PAPER "
        "OPERATIONS HANDOFF TEST"
    )
    print(line)
    print()
    print("V12.5 VALIDATION CHECKS")
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
    source, success = validate_success()
    second = validate_second_handoff(success)
    rejected = validate_non_approve_blocked(
        "REJECT",
        REJECT_REASON,
    )
    held = validate_non_approve_blocked(
        "HOLD",
        HOLD_REASON,
    )
    wrong_operator = validate_wrong_operator_blocked(
        source
    )
    wrong_text = validate_wrong_text_blocked(source)
    duplicate = validate_duplicate_blocked(
        source,
        success,
    )
    source_tampered = validate_source_tampering_failed(
        source
    )
    handoff_tampered = validate_handoff_tampering_failed(
        success
    )
    unsafe = validate_unsafe_source_failed(source)
    validate_save_and_load(second)
    print_checks(
        success,
        second,
        rejected,
        held,
        wrong_operator,
        wrong_text,
        duplicate,
        source_tampered,
        handoff_tampered,
        unsafe,
    )
    print()
    print(
        "V12.5 approved paper operations handoff "
        "test completed successfully."
    )
    print(
        "APPROVE 전용 Handoff, 수동 Operator 확인, 중복 "
        "차단 및 SHA-256 Hash Chain이 검증되었습니다."
    )
    print(
        "Paper 준비만 허용되며 Broker 주문과 Live "
        "Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
