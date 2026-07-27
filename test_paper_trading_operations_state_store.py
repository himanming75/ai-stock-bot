import io
import json
import uuid
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import backtest.paper_trading_operations_state_store as store_module
from backtest.paper_trading_operations_state_store import (
    GENESIS_STATE_HASH,
    PaperTradingOperationsStateStorePolicy,
    load_latest_paper_trading_operations_state_store,
    save_paper_trading_operations_state_store,
    update_paper_trading_operations_state_store,
    validate_state_store_policy,
    verify_saved_state_store_payload,
    verify_state_entry_chain,
)
from test_paper_trading_operations_console import (
    create_safe_v116_to_v119_chain,
    validate_ready_console,
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_ready_console() -> Any:
    (
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    ) = create_safe_v116_to_v119_chain()
    return run_silently(
        validate_ready_console,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )


def clone_console(
    console_result: Any,
    *,
    console_status: str | None = None,
    all_checks_passed: bool | None = None,
) -> Any:
    return replace(
        console_result,
        console_id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        console_status=(
            console_result.console_status
            if console_status is None
            else console_status
        ),
        all_checks_passed=(
            console_result.all_checks_passed
            if all_checks_passed is None
            else all_checks_passed
        ),
    )


def assert_execution_safety(result: Any) -> None:
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


def validate_first_state(console_result: Any) -> Any:
    result = run_silently(
        update_paper_trading_operations_state_store,
        console_result,
    )

    if result.version != "V12.1":
        raise RuntimeError(
            "State Store Version이 V12.1이 아닙니다."
        )
    if result.store_status != "UPDATED":
        raise RuntimeError(
            "첫 State 저장 상태가 UPDATED가 아닙니다."
        )
    if result.total_state_count != 1:
        raise RuntimeError(
            "첫 State Record 수가 1이 아닙니다."
        )
    if result.previous_console_status is not None:
        raise RuntimeError(
            "첫 State에 Previous Status가 있습니다."
        )
    if result.status_transition != "NONE -> READY":
        raise RuntimeError(
            "첫 Status Transition이 올바르지 않습니다."
        )
    if result.first_sequence_number != 1:
        raise RuntimeError(
            "첫 Sequence Number가 1이 아닙니다."
        )
    if (
        result.state_entries[0].previous_hash
        != GENESIS_STATE_HASH
    ):
        raise RuntimeError(
            "첫 State가 Genesis Hash에 연결되지 않았습니다."
        )
    if result.latest_console_id != console_result.console_id:
        raise RuntimeError(
            "Latest Console ID가 일치하지 않습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "첫 State 저장의 All Checks가 실패했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_second_state(
    ready_console: Any,
    first_result: Any,
) -> Any:
    review_console = clone_console(
        ready_console,
        console_status="REVIEW",
        all_checks_passed=False,
    )
    result = run_silently(
        update_paper_trading_operations_state_store,
        review_console,
        first_result.state_entries,
    )

    if result.store_status != "UPDATED":
        raise RuntimeError(
            "두 번째 State 저장이 UPDATED가 아닙니다."
        )
    if result.total_state_count != 2:
        raise RuntimeError(
            "두 번째 State Record 수가 2가 아닙니다."
        )
    if result.previous_console_status != "READY":
        raise RuntimeError(
            "Previous Console Status가 READY가 아닙니다."
        )
    if result.latest_console_status != "REVIEW":
        raise RuntimeError(
            "Latest Console Status가 REVIEW가 아닙니다."
        )
    if result.status_transition != "READY -> REVIEW":
        raise RuntimeError(
            "READY -> REVIEW 전환이 기록되지 않았습니다."
        )
    if (
        result.state_entries[1].previous_hash
        != result.state_entries[0].entry_hash
    ):
        raise RuntimeError(
            "두 번째 State Hash가 첫 State에 연결되지 않았습니다."
        )

    chain_valid, chain_errors = verify_state_entry_chain(
        result.state_entries
    )
    if not chain_valid or chain_errors:
        raise RuntimeError(
            "두 번째 State Hash Chain 검사가 실패했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_duplicate_block(
    console_result: Any,
    first_result: Any,
) -> Any:
    result = run_silently(
        update_paper_trading_operations_state_store,
        console_result,
        first_result.state_entries,
    )

    if result.store_status != "BLOCKED":
        raise RuntimeError(
            "중복 Console이 BLOCKED가 아닙니다."
        )
    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 Console 검사가 통과했습니다."
        )
    if result.total_state_count != 1:
        raise RuntimeError(
            "중복 차단 후 State Record가 변경됐습니다."
        )

    assert_execution_safety(result)
    return result


def validate_invalid_input() -> Any:
    result = run_silently(
        update_paper_trading_operations_state_store,
        {"version": "V12.0"},
    )

    if result.store_status != "FAILED":
        raise RuntimeError(
            "잘못된 입력이 FAILED가 아닙니다."
        )
    if result.input_checks_passed:
        raise RuntimeError(
            "잘못된 입력 검사가 통과했습니다."
        )
    if result.state_entries:
        raise RuntimeError(
            "잘못된 입력으로 State Entry가 생성됐습니다."
        )

    assert_execution_safety(result)
    return result


def validate_unsafe_console(console_result: Any) -> Any:
    unsafe_console = replace(
        console_result,
        read_only=False,
        execution_blocked=False,
        broker_api_called=True,
    )
    result = run_silently(
        update_paper_trading_operations_state_store,
        unsafe_console,
    )

    if result.store_status != "FAILED":
        raise RuntimeError(
            "위험한 Console이 FAILED가 아닙니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Console Safety 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_existing_chain_tampering(
    ready_console: Any,
    second_result: Any,
) -> Any:
    changed_entries = list(
        second_result.state_entries
    )
    changed_entries[0] = replace(
        changed_entries[0],
        console_status="FAILED",
    )
    new_console = clone_console(ready_console)
    result = run_silently(
        update_paper_trading_operations_state_store,
        new_console,
        tuple(changed_entries),
    )

    if result.store_status != "FAILED":
        raise RuntimeError(
            "변경된 기존 Chain이 FAILED가 아닙니다."
        )
    if result.existing_chain_checks_passed:
        raise RuntimeError(
            "변경된 기존 Chain 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_invalid_existing_entries(
    ready_console: Any,
) -> Any:
    result = run_silently(
        update_paper_trading_operations_state_store,
        ready_console,
        [{"console_id": "invalid"}],
    )

    if result.store_status != "FAILED":
        raise RuntimeError(
            "잘못된 Existing Entry가 FAILED가 아닙니다."
        )
    if result.existing_chain_checks_passed:
        raise RuntimeError(
            "잘못된 Existing Entry 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_history_limit(
    ready_console: Any,
) -> Any:
    entries: tuple[Any, ...] = ()
    last_result: Any = None

    for _ in range(101):
        console = clone_console(ready_console)
        last_result = run_silently(
            update_paper_trading_operations_state_store,
            console,
            entries,
        )
        if last_result.store_status != "UPDATED":
            raise RuntimeError(
                "History 생성 중 State 저장이 실패했습니다."
            )
        entries = last_result.state_entries

    if last_result.total_state_count != 100:
        raise RuntimeError(
            "State History 보관 개수가 100이 아닙니다."
        )
    if last_result.records_trimmed != 1:
        raise RuntimeError(
            "101번째 저장에서 Trim 수가 1이 아닙니다."
        )
    if last_result.first_sequence_number != 2:
        raise RuntimeError(
            "Trim 후 첫 Sequence가 2가 아닙니다."
        )
    if last_result.last_sequence_number != 101:
        raise RuntimeError(
            "Trim 후 마지막 Sequence가 101이 아닙니다."
        )

    chain_valid, chain_errors = verify_state_entry_chain(
        last_result.state_entries
    )
    if not chain_valid or chain_errors:
        raise RuntimeError(
            "Trim 후 State Hash Chain 검사가 실패했습니다."
        )

    assert_execution_safety(last_result)
    return last_result


def validate_policy_safety() -> None:
    policy = PaperTradingOperationsStateStorePolicy()
    policy_valid, policy_errors = (
        validate_state_store_policy(policy)
    )
    if not policy_valid or policy_errors:
        raise RuntimeError(
            "기본 V12.1 Policy가 유효하지 않습니다."
        )

    unsafe_policy = replace(
        policy,
        live_execution_disabled=False,
    )
    unsafe_valid, unsafe_errors = (
        validate_state_store_policy(
            unsafe_policy
        )
    )
    if unsafe_valid or not unsafe_errors:
        raise RuntimeError(
            "Live 허용 Policy가 차단되지 않았습니다."
        )

    invalid_hash_policy = replace(
        policy,
        hash_algorithm="MD5",
    )
    hash_valid, hash_errors = (
        validate_state_store_policy(
            invalid_hash_policy
        )
    )
    if hash_valid or not hash_errors:
        raise RuntimeError(
            "잘못된 Hash Policy가 차단되지 않았습니다."
        )

    try:
        policy.paper_only = False
    except FrozenInstanceError:
        pass
    else:
        raise RuntimeError(
            "State Store Policy가 변경되었습니다."
        )


def validate_save_load_and_file_tampering(
    successful_result: Any,
) -> None:
    original_directory = (
        store_module
        .PAPER_TRADING_OPERATIONS_STATE_STORE_OUTPUT_DIRECTORY
    )

    with TemporaryDirectory() as temporary_directory:
        store_module.PAPER_TRADING_OPERATIONS_STATE_STORE_OUTPUT_DIRECTORY = (
            Path(temporary_directory)
        )

        try:
            report_path, latest_path = (
                save_paper_trading_operations_state_store(
                    successful_result
                )
            )
            loaded = (
                load_latest_paper_trading_operations_state_store()
            )

            if not report_path.exists():
                raise RuntimeError(
                    "V12.1 Report 파일이 저장되지 않았습니다."
                )
            if not latest_path.exists():
                raise RuntimeError(
                    "V12.1 Latest 파일이 저장되지 않았습니다."
                )
            if loaded["version"] != "V12.1":
                raise RuntimeError(
                    "복원된 Version이 V12.1이 아닙니다."
                )
            if loaded["store_status"] != "UPDATED":
                raise RuntimeError(
                    "복원된 Store Status가 UPDATED가 아닙니다."
                )

            payload_valid, payload_errors = (
                verify_saved_state_store_payload(
                    loaded
                )
            )
            if not payload_valid or payload_errors:
                raise RuntimeError(
                    "복원된 State Hash 검사가 실패했습니다."
                )

            with latest_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                tampered_payload = json.load(file)
            tampered_payload["state_entries"][-1][
                "console_status"
            ] = "MANUALLY_CHANGED"
            with latest_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    tampered_payload,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            try:
                load_latest_paper_trading_operations_state_store()
            except RuntimeError:
                pass
            else:
                raise RuntimeError(
                    "변경된 State Store 파일이 탐지되지 않았습니다."
                )
        finally:
            store_module.PAPER_TRADING_OPERATIONS_STATE_STORE_OUTPUT_DIRECTORY = (
                original_directory
            )


def print_validation_checks(
    checks: list[tuple[str, bool]],
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("AI STOCK BOT V12.1 PAPER TRADING OPERATIONS STATE STORE TEST")
    print("=" * line_length)
    print()
    print("V12.1 VALIDATION CHECKS")
    print("-" * line_length)

    for label, passed in checks:
        print(f"{label:<70}: {passed}")

    print("=" * line_length)


def main() -> None:
    validate_policy_safety()
    ready_console = create_ready_console()

    first_result = validate_first_state(
        ready_console
    )
    second_result = validate_second_state(
        ready_console,
        first_result,
    )
    duplicate_result = validate_duplicate_block(
        ready_console,
        first_result,
    )
    invalid_input_result = validate_invalid_input()
    unsafe_result = validate_unsafe_console(
        ready_console
    )
    tampered_result = (
        validate_existing_chain_tampering(
            ready_console,
            second_result,
        )
    )
    invalid_entries_result = (
        validate_invalid_existing_entries(
            ready_console
        )
    )
    history_result = validate_history_limit(
        ready_console
    )
    validate_save_load_and_file_tampering(
        second_result
    )

    checks = [
        (
            "Version is V12.1",
            first_result.version == "V12.1",
        ),
        (
            "Default policy is valid",
            first_result.policy_checks_passed,
        ),
        (
            "Policy is immutable",
            True,
        ),
        (
            "Invalid policies are blocked",
            True,
        ),
        (
            "First console state was stored",
            first_result.store_status
            == "UPDATED",
        ),
        (
            "Genesis state hash was linked",
            first_result.state_entries[0]
            .previous_hash
            == GENESIS_STATE_HASH,
        ),
        (
            "Second console state was stored",
            second_result.total_state_count == 2,
        ),
        (
            "READY to REVIEW transition was recorded",
            second_result.status_transition
            == "READY -> REVIEW",
        ),
        (
            "State hash chain passed",
            second_result
            .updated_chain_checks_passed,
        ),
        (
            "Duplicate console was blocked",
            duplicate_result.store_status
            == "BLOCKED",
        ),
        (
            "Invalid input was failed",
            invalid_input_result.store_status
            == "FAILED",
        ),
        (
            "Unsafe console was failed",
            unsafe_result.store_status
            == "FAILED",
        ),
        (
            "Existing-chain tampering was detected",
            tampered_result.store_status
            == "FAILED",
        ),
        (
            "Invalid existing entries were blocked",
            invalid_entries_result.store_status
            == "FAILED",
        ),
        (
            "History was trimmed to 100 records",
            history_result.total_state_count
            == 100,
        ),
        (
            "Trimmed hash chain passed",
            history_result
            .updated_chain_checks_passed,
        ),
        (
            "Result save and load passed",
            True,
        ),
        (
            "Saved-file tampering was detected",
            True,
        ),
        (
            "Automatic execution remains disabled",
            not first_result
            .automatic_execution_authorized,
        ),
        (
            "Execution remains blocked",
            first_result.execution_blocked,
        ),
        (
            "Broker API was not called",
            not first_result.broker_api_called,
        ),
        (
            "Broker order was not created",
            not first_result.broker_order_created,
        ),
        (
            "Live order was not created",
            not first_result.live_order_created,
        ),
        (
            "Live execution not authorized",
            not first_result
            .live_execution_authorized,
        ),
    ]

    all_checks_passed = all(
        passed
        for _, passed in checks
    )
    checks.append(
        (
            "All checks passed",
            all_checks_passed,
        )
    )
    print_validation_checks(checks)

    if not all_checks_passed:
        raise RuntimeError(
            "V12.1 Validation Check가 실패했습니다."
        )

    print()
    print(
        "V12.1 paper trading operations state store test "
        "completed successfully."
    )
    print(
        "상태 누적, 전환 추적, SHA-256 Chain, 중복 및 "
        "변경 차단이 정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
