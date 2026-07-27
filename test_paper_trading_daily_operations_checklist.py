import io
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from backtest.paper_trading_daily_operations_checklist import (
    REQUIRED_CONFIRMATION_TEXT,
    PaperTradingDailyOperationsChecklistPolicy,
    build_paper_trading_daily_operations_checklist,
    load_latest_paper_trading_daily_operations_checklist,
    print_paper_trading_daily_operations_checklist,
    save_paper_trading_daily_operations_checklist,
    validate_checklist_policy,
    verify_saved_checklist_payload,
)
from test_paper_trading_operations_state_store import (
    create_ready_console,
    validate_first_state,
)


MANUAL_NOTE = "오늘 Paper Trading 운영 상태를 직접 확인했습니다."


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_safe_sources() -> tuple[Any, Any]:
    console_result = create_ready_console()
    state_store_result = validate_first_state(
        console_result
    )
    return console_result, state_store_result


def create_ready_checklist(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    return run_silently(
        build_paper_trading_daily_operations_checklist,
        console_result,
        state_store_result,
        console_result.manual_actor,
        REQUIRED_CONFIRMATION_TEXT,
        MANUAL_NOTE,
        date.today().isoformat(),
    )


def assert_execution_safety(result: Any) -> None:
    if not result.read_only:
        raise RuntimeError(
            "Checklist가 Read-Only가 아닙니다."
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


def validate_ready_result(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    result = create_ready_checklist(
        console_result,
        state_store_result,
    )
    if result.version != "V12.2":
        raise RuntimeError(
            "Checklist Version이 V12.2가 아닙니다."
        )
    if result.checklist_status != "READY":
        raise RuntimeError(
            "정상 Checklist가 READY가 아닙니다."
        )
    if result.total_item_count != 12:
        raise RuntimeError(
            "Checklist Item 수가 12개가 아닙니다."
        )
    if result.passed_item_count != 12:
        raise RuntimeError(
            "12개 Checklist Item이 모두 통과하지 않았습니다."
        )
    if result.blocked_item_count != 0:
        raise RuntimeError(
            "정상 Checklist에 BLOCKED Item이 있습니다."
        )
    if result.failed_item_count != 0:
        raise RuntimeError(
            "정상 Checklist에 FAILED Item이 있습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Checklist의 All Checks가 실패했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_wrong_confirmation(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    result = run_silently(
        build_paper_trading_daily_operations_checklist,
        console_result,
        state_store_result,
        console_result.manual_actor,
        "CONFIRM",
        MANUAL_NOTE,
    )
    if result.checklist_status != "BLOCKED":
        raise RuntimeError(
            "잘못된 확인 문구가 BLOCKED로 차단되지 않았습니다."
        )
    if result.manual_checks_passed:
        raise RuntimeError(
            "잘못된 확인 문구가 Manual 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_wrong_actor(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    result = run_silently(
        build_paper_trading_daily_operations_checklist,
        console_result,
        state_store_result,
        "wrong-actor",
        REQUIRED_CONFIRMATION_TEXT,
        MANUAL_NOTE,
    )
    if result.checklist_status != "BLOCKED":
        raise RuntimeError(
            "잘못된 Actor가 BLOCKED로 차단되지 않았습니다."
        )
    assert_execution_safety(result)
    return result


def validate_short_note(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    result = run_silently(
        build_paper_trading_daily_operations_checklist,
        console_result,
        state_store_result,
        console_result.manual_actor,
        REQUIRED_CONFIRMATION_TEXT,
        "짧음",
    )
    if result.checklist_status != "BLOCKED":
        raise RuntimeError(
            "짧은 Note가 BLOCKED로 차단되지 않았습니다."
        )
    assert_execution_safety(result)
    return result


def validate_console_not_ready(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    unsafe_status_console = replace(
        console_result,
        console_status="REVIEW",
        all_checks_passed=False,
    )
    result = run_silently(
        build_paper_trading_daily_operations_checklist,
        unsafe_status_console,
        state_store_result,
        unsafe_status_console.manual_actor,
        REQUIRED_CONFIRMATION_TEXT,
        MANUAL_NOTE,
    )
    if result.checklist_status != "BLOCKED":
        raise RuntimeError(
            "READY가 아닌 Console이 BLOCKED로 차단되지 않았습니다."
        )
    if result.source_status_checks_passed:
        raise RuntimeError(
            "READY가 아닌 Console이 Source Status 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_identity_mismatch(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    mismatched_store = replace(
        state_store_result,
        latest_console_id="wrong-console-id",
    )
    result = run_silently(
        build_paper_trading_daily_operations_checklist,
        console_result,
        mismatched_store,
        console_result.manual_actor,
        REQUIRED_CONFIRMATION_TEXT,
        MANUAL_NOTE,
    )
    if result.checklist_status != "FAILED":
        raise RuntimeError(
            "Console ID 불일치가 FAILED로 차단되지 않았습니다."
        )
    if result.source_identity_checks_passed:
        raise RuntimeError(
            "Console ID 불일치가 Identity 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_tampered_hash(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    entry = state_store_result.state_entries[-1]
    tampered_entry = replace(
        entry,
        console_status="REVIEW",
    )
    tampered_store = replace(
        state_store_result,
        state_entries=(tampered_entry,),
    )
    result = run_silently(
        build_paper_trading_daily_operations_checklist,
        console_result,
        tampered_store,
        console_result.manual_actor,
        REQUIRED_CONFIRMATION_TEXT,
        MANUAL_NOTE,
    )
    if result.checklist_status != "FAILED":
        raise RuntimeError(
            "변경된 State Hash가 FAILED로 차단되지 않았습니다."
        )
    if result.state_hash_chain_checks_passed:
        raise RuntimeError(
            "변경된 State Hash가 Chain 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_unsafe_source(
    console_result: Any,
    state_store_result: Any,
) -> Any:
    unsafe_console = replace(
        console_result,
        broker_api_called=True,
        execution_blocked=False,
    )
    result = run_silently(
        build_paper_trading_daily_operations_checklist,
        unsafe_console,
        state_store_result,
        unsafe_console.manual_actor,
        REQUIRED_CONFIRMATION_TEXT,
        MANUAL_NOTE,
    )
    if result.checklist_status != "FAILED":
        raise RuntimeError(
            "위험한 Source가 FAILED로 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Source가 Safety 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_invalid_inputs() -> Any:
    result = run_silently(
        build_paper_trading_daily_operations_checklist,
        None,
        None,
        None,
        None,
        None,
        "2026-99-99",
    )
    if result.checklist_status != "FAILED":
        raise RuntimeError(
            "잘못된 입력이 FAILED로 처리되지 않았습니다."
        )
    if result.input_checks_passed:
        raise RuntimeError(
            "잘못된 입력이 Input 검사를 통과했습니다."
        )
    assert_execution_safety(result)
    return result


def validate_policy() -> None:
    policy = (
        PaperTradingDailyOperationsChecklistPolicy()
    )
    valid, errors = validate_checklist_policy(policy)
    if not valid or errors:
        raise RuntimeError(
            "기본 Checklist Policy가 유효하지 않습니다."
        )

    try:
        policy.minimum_note_length = 1
        raise RuntimeError(
            "Checklist Policy가 변경되었습니다."
        )
    except FrozenInstanceError:
        pass

    invalid_policy = replace(
        policy,
        automatic_execution_disabled=False,
    )
    valid, errors = validate_checklist_policy(
        invalid_policy
    )
    if valid or not errors:
        raise RuntimeError(
            "위험한 Checklist Policy가 차단되지 않았습니다."
        )


def validate_save_and_load(result: Any) -> None:
    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)
        saved_result = (
            save_paper_trading_daily_operations_checklist(
                result,
                directory,
            )
        )
        if not saved_result.report_path:
            raise RuntimeError(
                "Checklist Report Path가 없습니다."
            )
        if not saved_result.latest_path:
            raise RuntimeError(
                "Checklist Latest Path가 없습니다."
            )

        loaded = (
            load_latest_paper_trading_daily_operations_checklist(
                directory
            )
        )
        valid, errors = verify_saved_checklist_payload(
            loaded
        )
        if not valid or errors:
            raise RuntimeError(
                "저장된 Checklist 검증에 실패했습니다."
            )
        if loaded["checklist_id"] != result.checklist_id:
            raise RuntimeError(
                "저장 후 Checklist ID가 변경되었습니다."
            )


def print_validation_checks(
    ready_result: Any,
    wrong_confirmation_result: Any,
    wrong_actor_result: Any,
    short_note_result: Any,
    not_ready_result: Any,
    mismatch_result: Any,
    tampered_result: Any,
    unsafe_result: Any,
    invalid_result: Any,
) -> None:
    checks = {
        "Version is V12.2": (
            ready_result.version == "V12.2"
        ),
        "Default policy is valid": (
            ready_result.policy_checks_passed
        ),
        "Policy is immutable": True,
        "Invalid policies are blocked": True,
        "Twelve checklist items were created": (
            ready_result.total_item_count == 12
        ),
        "All checklist items passed": (
            ready_result.passed_item_count == 12
        ),
        "READY checklist was created": (
            ready_result.checklist_status == "READY"
        ),
        "Wrong confirmation was blocked": (
            wrong_confirmation_result.checklist_status
            == "BLOCKED"
        ),
        "Wrong actor was blocked": (
            wrong_actor_result.checklist_status
            == "BLOCKED"
        ),
        "Short note was blocked": (
            short_note_result.checklist_status
            == "BLOCKED"
        ),
        "Non-ready console was blocked": (
            not_ready_result.checklist_status
            == "BLOCKED"
        ),
        "Console ID mismatch failed": (
            mismatch_result.checklist_status
            == "FAILED"
        ),
        "State hash tampering failed": (
            tampered_result.checklist_status
            == "FAILED"
        ),
        "Unsafe source failed": (
            unsafe_result.checklist_status
            == "FAILED"
        ),
        "Invalid input failed": (
            invalid_result.checklist_status
            == "FAILED"
        ),
        "Result save and load passed": True,
        "Automatic execution remains disabled": (
            not ready_result
            .automatic_execution_authorized
        ),
        "Execution remains blocked": (
            ready_result.execution_blocked
        ),
        "Broker API was not called": (
            not ready_result.broker_api_called
        ),
        "Broker order was not created": (
            not ready_result.broker_order_created
        ),
        "Live order was not created": (
            not ready_result.live_order_created
        ),
        "Live execution not authorized": (
            not ready_result
            .live_execution_authorized
        ),
        "All checks passed": (
            ready_result.all_checks_passed
        ),
    }

    line = "=" * 100
    print()
    print(line)
    print(
        "AI STOCK BOT V12.2 DAILY OPERATIONS "
        "CHECKLIST TEST"
    )
    print(line)
    print()
    print("V12.2 VALIDATION CHECKS")
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
    console_result, state_store_result = (
        create_safe_sources()
    )
    ready_result = validate_ready_result(
        console_result,
        state_store_result,
    )
    wrong_confirmation_result = (
        validate_wrong_confirmation(
            console_result,
            state_store_result,
        )
    )
    wrong_actor_result = validate_wrong_actor(
        console_result,
        state_store_result,
    )
    short_note_result = validate_short_note(
        console_result,
        state_store_result,
    )
    not_ready_result = validate_console_not_ready(
        console_result,
        state_store_result,
    )
    mismatch_result = validate_identity_mismatch(
        console_result,
        state_store_result,
    )
    tampered_result = validate_tampered_hash(
        console_result,
        state_store_result,
    )
    unsafe_result = validate_unsafe_source(
        console_result,
        state_store_result,
    )
    invalid_result = validate_invalid_inputs()
    validate_save_and_load(ready_result)

    run_silently(
        print_paper_trading_daily_operations_checklist,
        ready_result,
    )
    print_validation_checks(
        ready_result,
        wrong_confirmation_result,
        wrong_actor_result,
        short_note_result,
        not_ready_result,
        mismatch_result,
        tampered_result,
        unsafe_result,
        invalid_result,
    )
    print()
    print(
        "V12.2 paper trading daily operations checklist "
        "test completed successfully."
    )
    print(
        "12개 일일 운영 항목, 수동 확인, Source 연결, "
        "Hash Chain 및 안전 차단이 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
