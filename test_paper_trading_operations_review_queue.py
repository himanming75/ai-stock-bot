import io
import uuid
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from backtest.paper_trading_operations_review_queue import (
    GENESIS_QUEUE_HASH,
    PaperTradingOperationsReviewQueuePolicy,
    enqueue_paper_trading_operations_review,
    load_latest_paper_trading_operations_review_queue,
    print_paper_trading_operations_review_queue,
    save_paper_trading_operations_review_queue,
    validate_review_queue_policy,
    verify_review_queue_hash_chain,
    verify_saved_review_queue_payload,
)
from test_paper_trading_daily_operations_checklist import (
    create_ready_checklist,
    create_safe_sources,
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_ready_source() -> Any:
    console_result, state_store_result = (
        create_safe_sources()
    )
    return create_ready_checklist(
        console_result,
        state_store_result,
    )


def assert_execution_safety(result: Any) -> None:
    if not result.manual_review_required:
        raise RuntimeError(
            "Manual Review가 필수가 아닙니다."
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


def validate_first_queue_item(
    checklist_result: Any,
) -> Any:
    result = run_silently(
        enqueue_paper_trading_operations_review,
        checklist_result,
        None,
        "NORMAL",
        "첫 번째 수동 검토 대기 항목",
    )
    if result.version != "V12.3":
        raise RuntimeError(
            "Review Queue Version이 V12.3이 아닙니다."
        )
    if result.queue_status != "UPDATED":
        raise RuntimeError(
            "첫 Review Queue 등록이 UPDATED가 아닙니다."
        )
    if result.total_queue_count != 1:
        raise RuntimeError(
            "첫 Queue Item 수가 1이 아닙니다."
        )
    if result.pending_review_count != 1:
        raise RuntimeError(
            "첫 Pending Review 수가 1이 아닙니다."
        )
    if result.queue_items[0].previous_hash != GENESIS_QUEUE_HASH:
        raise RuntimeError(
            "첫 Queue Item이 Genesis Hash에 연결되지 않았습니다."
        )
    if result.queue_items[0].review_status != "PENDING":
        raise RuntimeError(
            "첫 Queue Item이 PENDING이 아닙니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "첫 Queue 등록의 All Checks가 실패했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_second_queue_item(
    first_result: Any,
) -> tuple[Any, Any]:
    second_checklist = create_ready_source()
    result = run_silently(
        enqueue_paper_trading_operations_review,
        second_checklist,
        first_result.queue_items,
        "HIGH",
        "우선 검토가 필요한 항목",
    )
    if result.queue_status != "UPDATED":
        raise RuntimeError(
            "두 번째 Review Queue 등록이 UPDATED가 아닙니다."
        )
    if result.total_queue_count != 2:
        raise RuntimeError(
            "두 번째 Queue Item 등록 후 수가 2가 아닙니다."
        )
    if result.pending_review_count != 2:
        raise RuntimeError(
            "Pending Review 수가 2가 아닙니다."
        )
    if result.high_priority_count != 1:
        raise RuntimeError(
            "High Priority 수가 1이 아닙니다."
        )
    chain_valid, chain_errors = (
        verify_review_queue_hash_chain(
            result.queue_items
        )
    )
    if not chain_valid or chain_errors:
        raise RuntimeError(
            "두 Queue Item의 Hash Chain이 실패했습니다."
        )
    assert_execution_safety(result)
    return second_checklist, result


def validate_duplicate_blocked(
    checklist_result: Any,
    queue_result: Any,
) -> Any:
    result = run_silently(
        enqueue_paper_trading_operations_review,
        checklist_result,
        queue_result.queue_items,
    )
    if result.queue_status != "BLOCKED":
        raise RuntimeError(
            "중복 Checklist가 BLOCKED로 차단되지 않았습니다."
        )
    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 Checklist가 Duplicate 검사를 통과했습니다."
        )
    if result.total_queue_count != 2:
        raise RuntimeError(
            "중복 차단 후 Queue Item 수가 변경되었습니다."
        )
    assert_execution_safety(result)
    return result


def validate_non_ready_blocked(
    checklist_result: Any,
) -> Any:
    blocked_checklist = replace(
        checklist_result,
        checklist_id=str(uuid.uuid4()),
        checklist_status="BLOCKED",
        all_checks_passed=False,
    )
    result = run_silently(
        enqueue_paper_trading_operations_review,
        blocked_checklist,
    )
    if result.queue_status != "BLOCKED":
        raise RuntimeError(
            "READY가 아닌 Checklist가 BLOCKED로 차단되지 않았습니다."
        )
    if result.queue_checks_passed:
        raise RuntimeError(
            "READY가 아닌 Checklist가 Queue 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_tampered_queue_failed(
    checklist_result: Any,
    queue_result: Any,
) -> Any:
    first_item = queue_result.queue_items[0]
    tampered_item = replace(
        first_item,
        priority="HIGH",
    )
    result = run_silently(
        enqueue_paper_trading_operations_review,
        checklist_result,
        (
            tampered_item,
            *queue_result.queue_items[1:],
        ),
    )
    if result.queue_status != "FAILED":
        raise RuntimeError(
            "변경된 Queue Hash가 FAILED로 차단되지 않았습니다."
        )
    if result.existing_chain_checks_passed:
        raise RuntimeError(
            "변경된 Queue가 Hash Chain 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_unsafe_source_failed(
    checklist_result: Any,
) -> Any:
    unsafe_checklist = replace(
        checklist_result,
        checklist_id=str(uuid.uuid4()),
        broker_api_called=True,
        execution_blocked=False,
    )
    result = run_silently(
        enqueue_paper_trading_operations_review,
        unsafe_checklist,
    )
    if result.queue_status != "FAILED":
        raise RuntimeError(
            "위험한 Checklist가 FAILED로 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Checklist가 Safety 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_invalid_priority_failed(
    checklist_result: Any,
) -> Any:
    result = run_silently(
        enqueue_paper_trading_operations_review,
        checklist_result,
        None,
        "URGENT",
    )
    if result.queue_status != "FAILED":
        raise RuntimeError(
            "잘못된 Priority가 FAILED로 처리되지 않았습니다."
        )
    if result.input_checks_passed:
        raise RuntimeError(
            "잘못된 Priority가 Input 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_invalid_source_failed() -> Any:
    result = run_silently(
        enqueue_paper_trading_operations_review,
        None,
    )
    if result.queue_status != "FAILED":
        raise RuntimeError(
            "잘못된 Source가 FAILED로 처리되지 않았습니다."
        )
    assert_execution_safety(result)
    return result


def validate_history_trim(
    checklist_result: Any,
    first_result: Any,
) -> Any:
    limited_policy = (
        PaperTradingOperationsReviewQueuePolicy(
            maximum_queue_records=1
        )
    )
    new_checklist = replace(
        checklist_result,
        checklist_id=str(uuid.uuid4()),
    )
    result = run_silently(
        enqueue_paper_trading_operations_review,
        new_checklist,
        first_result.queue_items,
        "NORMAL",
        None,
        limited_policy,
    )
    if result.queue_status != "UPDATED":
        raise RuntimeError(
            "Queue Trim 등록이 UPDATED가 아닙니다."
        )
    if result.total_queue_count != 1:
        raise RuntimeError(
            "Queue History가 1개로 정리되지 않았습니다."
        )
    if result.records_trimmed != 1:
        raise RuntimeError(
            "Trimmed Record 수가 1이 아닙니다."
        )
    chain_valid, chain_errors = (
        verify_review_queue_hash_chain(
            result.queue_items
        )
    )
    if not chain_valid or chain_errors:
        raise RuntimeError(
            "Trim 후 Hash Chain 검사가 실패했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_policy() -> None:
    policy = PaperTradingOperationsReviewQueuePolicy()
    valid, errors = validate_review_queue_policy(policy)
    if not valid or errors:
        raise RuntimeError(
            "기본 Review Queue Policy가 유효하지 않습니다."
        )
    try:
        policy.maximum_queue_records = 1
        raise RuntimeError(
            "Review Queue Policy가 변경되었습니다."
        )
    except FrozenInstanceError:
        pass

    invalid_policy = replace(
        policy,
        automatic_execution_disabled=False,
    )
    valid, errors = validate_review_queue_policy(
        invalid_policy
    )
    if valid or not errors:
        raise RuntimeError(
            "위험한 Review Queue Policy가 차단되지 않았습니다."
        )


def validate_save_and_load(result: Any) -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        saved_result = (
            save_paper_trading_operations_review_queue(
                result,
                directory,
            )
        )
        if not saved_result.report_path:
            raise RuntimeError(
                "Review Queue Report Path가 없습니다."
            )
        if not saved_result.latest_path:
            raise RuntimeError(
                "Review Queue Latest Path가 없습니다."
            )
        loaded = (
            load_latest_paper_trading_operations_review_queue(
                directory
            )
        )
        valid, errors = (
            verify_saved_review_queue_payload(
                loaded
            )
        )
        if not valid or errors:
            raise RuntimeError(
                "저장된 Review Queue 검증에 실패했습니다."
            )
        if (
            loaded["review_queue_id"]
            != result.review_queue_id
        ):
            raise RuntimeError(
                "저장 후 Review Queue ID가 변경되었습니다."
            )


def print_validation_checks(
    first_result: Any,
    second_result: Any,
    duplicate_result: Any,
    blocked_result: Any,
    tampered_result: Any,
    unsafe_result: Any,
    invalid_priority_result: Any,
    invalid_source_result: Any,
    trimmed_result: Any,
) -> None:
    checks = {
        "Version is V12.3": (
            first_result.version == "V12.3"
        ),
        "Default policy is valid": (
            first_result.policy_checks_passed
        ),
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "First checklist was queued": (
            first_result.queue_status == "UPDATED"
        ),
        "Second checklist was queued": (
            second_result.total_queue_count == 2
        ),
        "Two pending reviews were counted": (
            second_result.pending_review_count == 2
        ),
        "High priority was counted": (
            second_result.high_priority_count == 1
        ),
        "Queue hash chain passed": (
            second_result.updated_chain_checks_passed
        ),
        "Duplicate checklist was blocked": (
            duplicate_result.queue_status == "BLOCKED"
        ),
        "Non-ready checklist was blocked": (
            blocked_result.queue_status == "BLOCKED"
        ),
        "Queue tampering failed": (
            tampered_result.queue_status == "FAILED"
        ),
        "Unsafe checklist failed": (
            unsafe_result.queue_status == "FAILED"
        ),
        "Invalid priority failed": (
            invalid_priority_result.queue_status == "FAILED"
        ),
        "Invalid source failed": (
            invalid_source_result.queue_status == "FAILED"
        ),
        "Oldest queue item was trimmed": (
            trimmed_result.records_trimmed == 1
        ),
        "Result save and load passed": True,
        "Manual review remains required": (
            first_result.manual_review_required
        ),
        "Automatic execution remains disabled": (
            not first_result
            .automatic_execution_authorized
        ),
        "Execution remains blocked": (
            first_result.execution_blocked
        ),
        "Broker API was not called": (
            not first_result.broker_api_called
        ),
        "Broker order was not created": (
            not first_result.broker_order_created
        ),
        "Live order was not created": (
            not first_result.live_order_created
        ),
        "Live execution not authorized": (
            not first_result
            .live_execution_authorized
        ),
        "All checks passed": (
            first_result.all_checks_passed
            and second_result.all_checks_passed
        ),
    }
    line = "=" * 100
    print()
    print(line)
    print(
        "AI STOCK BOT V12.3 PAPER TRADING "
        "OPERATIONS REVIEW QUEUE TEST"
    )
    print(line)
    print()
    print("V12.3 VALIDATION CHECKS")
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
    first_checklist = create_ready_source()
    first_result = validate_first_queue_item(
        first_checklist
    )
    second_checklist, second_result = (
        validate_second_queue_item(first_result)
    )
    duplicate_result = validate_duplicate_blocked(
        second_checklist,
        second_result,
    )
    blocked_result = validate_non_ready_blocked(
        create_ready_source()
    )
    tampered_result = validate_tampered_queue_failed(
        create_ready_source(),
        second_result,
    )
    unsafe_result = validate_unsafe_source_failed(
        create_ready_source()
    )
    invalid_priority_result = (
        validate_invalid_priority_failed(
            create_ready_source()
        )
    )
    invalid_source_result = (
        validate_invalid_source_failed()
    )
    trimmed_result = validate_history_trim(
        create_ready_source(),
        first_result,
    )
    validate_save_and_load(second_result)

    run_silently(
        print_paper_trading_operations_review_queue,
        second_result,
    )
    print_validation_checks(
        first_result,
        second_result,
        duplicate_result,
        blocked_result,
        tampered_result,
        unsafe_result,
        invalid_priority_result,
        invalid_source_result,
        trimmed_result,
    )
    print()
    print(
        "V12.3 paper trading operations review queue "
        "test completed successfully."
    )
    print(
        "수동 검토 Queue, 우선순위, 중복 차단, SHA-256 "
        "Hash Chain 및 기록 제한이 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
