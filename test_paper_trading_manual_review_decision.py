import io
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from backtest.paper_trading_manual_review_decision import (
    DECISION_CONFIRMATION_TEXTS,
    GENESIS_DECISION_HASH,
    PaperTradingManualReviewDecisionPolicy,
    load_latest_paper_trading_manual_review_decision,
    print_paper_trading_manual_review_decision,
    record_paper_trading_manual_review_decision,
    save_paper_trading_manual_review_decision,
    validate_decision_policy,
    verify_decision_record_chain,
    verify_saved_manual_review_decision_payload,
)
from test_paper_trading_operations_review_queue import (
    create_ready_source,
    validate_first_queue_item,
    validate_second_queue_item,
)


REVIEWER = "manual-reviewer"
APPROVE_REASON = "모든 Paper 운영 점검 항목을 직접 확인했습니다."
REJECT_REASON = "운영 위험 항목이 확인되어 이번 실행을 거부합니다."
HOLD_REASON = "추가 자료 확인이 필요하여 검토를 잠시 보류합니다."


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_queue_with_two_items() -> Any:
    first_checklist = create_ready_source()
    first_queue = validate_first_queue_item(
        first_checklist
    )
    _, second_queue = validate_second_queue_item(
        first_queue
    )
    return second_queue


def assert_execution_safety(result: Any) -> None:
    if not result.manual_decision_required:
        raise RuntimeError(
            "Manual Decision이 필수가 아닙니다."
        )
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


def record_decision(
    queue_result: Any,
    item_index: int,
    decision: str,
    reason: str,
    existing_records: Any = None,
) -> Any:
    return run_silently(
        record_paper_trading_manual_review_decision,
        queue_result,
        queue_result.queue_items[item_index]
        .queue_item_id,
        decision,
        REVIEWER,
        reason,
        DECISION_CONFIRMATION_TEXTS[decision],
        existing_records,
    )


def validate_approve(queue_result: Any) -> Any:
    result = record_decision(
        queue_result,
        0,
        "APPROVE",
        APPROVE_REASON,
    )
    if result.version != "V12.4":
        raise RuntimeError(
            "Manual Decision Version이 V12.4가 아닙니다."
        )
    if result.result_status != "RECORDED":
        raise RuntimeError(
            "APPROVE 판정이 RECORDED가 아닙니다."
        )
    if result.decision != "APPROVE":
        raise RuntimeError(
            "Decision이 APPROVE가 아닙니다."
        )
    if result.next_review_status != "APPROVED":
        raise RuntimeError(
            "Next Review Status가 APPROVED가 아닙니다."
        )
    if result.total_decision_count != 1:
        raise RuntimeError(
            "첫 Decision Record 수가 1이 아닙니다."
        )
    if (
        result.decision_records[0].previous_hash
        != GENESIS_DECISION_HASH
    ):
        raise RuntimeError(
            "첫 Decision이 Genesis Hash에 연결되지 않았습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "APPROVE의 All Checks가 실패했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_reject_and_chain(
    queue_result: Any,
    approve_result: Any,
) -> Any:
    result = record_decision(
        queue_result,
        1,
        "REJECT",
        REJECT_REASON,
        approve_result.decision_records,
    )
    if result.result_status != "RECORDED":
        raise RuntimeError(
            "REJECT 판정이 RECORDED가 아닙니다."
        )
    if result.reject_count != 1:
        raise RuntimeError(
            "REJECT Count가 1이 아닙니다."
        )
    if result.total_decision_count != 2:
        raise RuntimeError(
            "Decision Record 수가 2가 아닙니다."
        )
    valid, errors = verify_decision_record_chain(
        result.decision_records
    )
    if not valid or errors:
        raise RuntimeError(
            "Decision Hash Chain 검사가 실패했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_hold() -> Any:
    queue_result = create_queue_with_two_items()
    result = record_decision(
        queue_result,
        0,
        "HOLD",
        HOLD_REASON,
    )
    if result.result_status != "RECORDED":
        raise RuntimeError(
            "HOLD 판정이 RECORDED가 아닙니다."
        )
    if result.next_review_status != "ON_HOLD":
        raise RuntimeError(
            "Next Review Status가 ON_HOLD가 아닙니다."
        )
    assert_execution_safety(result)
    return result


def validate_wrong_confirmation_blocked(
    queue_result: Any,
) -> Any:
    result = run_silently(
        record_paper_trading_manual_review_decision,
        queue_result,
        queue_result.queue_items[0].queue_item_id,
        "APPROVE",
        REVIEWER,
        APPROVE_REASON,
        "APPROVE",
    )
    if result.result_status != "BLOCKED":
        raise RuntimeError(
            "잘못된 확인 문구가 BLOCKED로 차단되지 않았습니다."
        )
    if result.manual_checks_passed:
        raise RuntimeError(
            "잘못된 확인 문구가 Manual 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_short_reason_blocked(
    queue_result: Any,
) -> Any:
    result = run_silently(
        record_paper_trading_manual_review_decision,
        queue_result,
        queue_result.queue_items[0].queue_item_id,
        "HOLD",
        REVIEWER,
        "짧음",
        DECISION_CONFIRMATION_TEXTS["HOLD"],
    )
    if result.result_status != "BLOCKED":
        raise RuntimeError(
            "짧은 사유가 BLOCKED로 차단되지 않았습니다."
        )
    assert_execution_safety(result)
    return result


def validate_missing_item_blocked(
    queue_result: Any,
) -> Any:
    result = run_silently(
        record_paper_trading_manual_review_decision,
        queue_result,
        "missing-item-id",
        "REJECT",
        REVIEWER,
        REJECT_REASON,
        DECISION_CONFIRMATION_TEXTS["REJECT"],
    )
    if result.result_status != "BLOCKED":
        raise RuntimeError(
            "없는 Queue Item이 BLOCKED로 차단되지 않았습니다."
        )
    if result.target_item_checks_passed:
        raise RuntimeError(
            "없는 Queue Item이 Target 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_duplicate_blocked(
    queue_result: Any,
    approve_result: Any,
) -> Any:
    result = record_decision(
        queue_result,
        0,
        "APPROVE",
        APPROVE_REASON,
        approve_result.decision_records,
    )
    if result.result_status != "BLOCKED":
        raise RuntimeError(
            "중복 Decision이 BLOCKED로 차단되지 않았습니다."
        )
    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 Decision이 Duplicate 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_queue_tampering_failed(
    queue_result: Any,
) -> Any:
    tampered_item = replace(
        queue_result.queue_items[0],
        priority="HIGH",
    )
    tampered_queue = replace(
        queue_result,
        queue_items=(
            tampered_item,
            *queue_result.queue_items[1:],
        ),
    )
    result = run_silently(
        record_paper_trading_manual_review_decision,
        tampered_queue,
        tampered_item.queue_item_id,
        "REJECT",
        REVIEWER,
        REJECT_REASON,
        DECISION_CONFIRMATION_TEXTS["REJECT"],
    )
    if result.result_status != "FAILED":
        raise RuntimeError(
            "변경된 Queue Hash가 FAILED로 차단되지 않았습니다."
        )
    if result.queue_hash_chain_checks_passed:
        raise RuntimeError(
            "변경된 Queue가 Hash Chain 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_decision_tampering_failed(
    queue_result: Any,
    approve_result: Any,
) -> Any:
    tampered_record = replace(
        approve_result.decision_records[0],
        decision="HOLD",
    )
    result = record_decision(
        queue_result,
        1,
        "REJECT",
        REJECT_REASON,
        (tampered_record,),
    )
    if result.result_status != "FAILED":
        raise RuntimeError(
            "변경된 Decision Hash가 FAILED로 차단되지 않았습니다."
        )
    if result.existing_decision_chain_checks_passed:
        raise RuntimeError(
            "변경된 Decision이 Hash Chain 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_unsafe_source_failed(
    queue_result: Any,
) -> Any:
    unsafe_queue = replace(
        queue_result,
        broker_api_called=True,
        execution_blocked=False,
    )
    result = run_silently(
        record_paper_trading_manual_review_decision,
        unsafe_queue,
        unsafe_queue.queue_items[0].queue_item_id,
        "REJECT",
        REVIEWER,
        REJECT_REASON,
        DECISION_CONFIRMATION_TEXTS["REJECT"],
    )
    if result.result_status != "FAILED":
        raise RuntimeError(
            "위험한 Queue가 FAILED로 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Queue가 Safety 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_policy() -> None:
    policy = PaperTradingManualReviewDecisionPolicy()
    valid, errors = validate_decision_policy(policy)
    if not valid or errors:
        raise RuntimeError(
            "기본 Decision Policy가 유효하지 않습니다."
        )
    try:
        policy.minimum_reason_length = 1
        raise RuntimeError(
            "Decision Policy가 변경되었습니다."
        )
    except FrozenInstanceError:
        pass
    invalid_policy = replace(
        policy,
        automatic_execution_disabled=False,
    )
    valid, errors = validate_decision_policy(
        invalid_policy
    )
    if valid or not errors:
        raise RuntimeError(
            "위험한 Decision Policy가 차단되지 않았습니다."
        )


def validate_save_and_load(result: Any) -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        saved = save_paper_trading_manual_review_decision(
            result,
            directory,
        )
        if not saved.report_path or not saved.latest_path:
            raise RuntimeError(
                "Decision 저장 경로가 생성되지 않았습니다."
            )
        loaded = (
            load_latest_paper_trading_manual_review_decision(
                directory
            )
        )
        valid, errors = (
            verify_saved_manual_review_decision_payload(
                loaded
            )
        )
        if not valid or errors:
            raise RuntimeError(
                "저장된 Decision 검증에 실패했습니다."
            )
        if (
            loaded["manual_review_decision_id"]
            != result.manual_review_decision_id
        ):
            raise RuntimeError(
                "저장 후 Manual Decision ID가 변경되었습니다."
            )


def print_validation_checks(
    approve_result: Any,
    reject_result: Any,
    hold_result: Any,
    wrong_text_result: Any,
    short_reason_result: Any,
    missing_item_result: Any,
    duplicate_result: Any,
    queue_tampered_result: Any,
    decision_tampered_result: Any,
    unsafe_result: Any,
) -> None:
    checks = {
        "Version is V12.4": (
            approve_result.version == "V12.4"
        ),
        "Default policy is valid": (
            approve_result.policy_checks_passed
        ),
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "APPROVE decision was recorded": (
            approve_result.result_status == "RECORDED"
        ),
        "REJECT decision was recorded": (
            reject_result.reject_count == 1
        ),
        "HOLD decision was recorded": (
            hold_result.hold_count == 1
        ),
        "Decision hash chain passed": (
            reject_result
            .updated_decision_chain_checks_passed
        ),
        "Wrong confirmation was blocked": (
            wrong_text_result.result_status == "BLOCKED"
        ),
        "Short reason was blocked": (
            short_reason_result.result_status == "BLOCKED"
        ),
        "Missing queue item was blocked": (
            missing_item_result.result_status == "BLOCKED"
        ),
        "Duplicate decision was blocked": (
            duplicate_result.result_status == "BLOCKED"
        ),
        "Queue tampering failed": (
            queue_tampered_result.result_status == "FAILED"
        ),
        "Decision tampering failed": (
            decision_tampered_result.result_status == "FAILED"
        ),
        "Unsafe queue failed": (
            unsafe_result.result_status == "FAILED"
        ),
        "Result save and load passed": True,
        "Manual decision remains required": (
            approve_result.manual_decision_required
        ),
        "Paper execution remains unauthorized": (
            not approve_result.paper_execution_authorized
        ),
        "Automatic execution remains disabled": (
            not approve_result
            .automatic_execution_authorized
        ),
        "Execution remains blocked": (
            approve_result.execution_blocked
        ),
        "Broker API was not called": (
            not approve_result.broker_api_called
        ),
        "Broker order was not created": (
            not approve_result.broker_order_created
        ),
        "Live order was not created": (
            not approve_result.live_order_created
        ),
        "Live execution not authorized": (
            not approve_result
            .live_execution_authorized
        ),
        "All checks passed": (
            approve_result.all_checks_passed
            and reject_result.all_checks_passed
            and hold_result.all_checks_passed
        ),
    }
    line = "=" * 100
    print()
    print(line)
    print(
        "AI STOCK BOT V12.4 PAPER TRADING "
        "MANUAL REVIEW DECISION TEST"
    )
    print(line)
    print()
    print("V12.4 VALIDATION CHECKS")
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
    queue_result = create_queue_with_two_items()
    approve_result = validate_approve(queue_result)
    reject_result = validate_reject_and_chain(
        queue_result,
        approve_result,
    )
    hold_result = validate_hold()
    wrong_text_result = (
        validate_wrong_confirmation_blocked(
            queue_result
        )
    )
    short_reason_result = validate_short_reason_blocked(
        queue_result
    )
    missing_item_result = validate_missing_item_blocked(
        queue_result
    )
    duplicate_result = validate_duplicate_blocked(
        queue_result,
        approve_result,
    )
    queue_tampered_result = (
        validate_queue_tampering_failed(
            queue_result
        )
    )
    decision_tampered_result = (
        validate_decision_tampering_failed(
            queue_result,
            approve_result,
        )
    )
    unsafe_result = validate_unsafe_source_failed(
        queue_result
    )
    validate_save_and_load(reject_result)

    run_silently(
        print_paper_trading_manual_review_decision,
        reject_result,
    )
    print_validation_checks(
        approve_result,
        reject_result,
        hold_result,
        wrong_text_result,
        short_reason_result,
        missing_item_result,
        duplicate_result,
        queue_tampered_result,
        decision_tampered_result,
        unsafe_result,
    )
    print()
    print(
        "V12.4 paper trading manual review decision "
        "test completed successfully."
    )
    print(
        "APPROVE, REJECT, HOLD 수동 판정, 확인 문구, "
        "중복 차단 및 SHA-256 Hash Chain이 검증되었습니다."
    )
    print(
        "APPROVE도 Broker 주문 권한이 아니며 실제 주문과 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
