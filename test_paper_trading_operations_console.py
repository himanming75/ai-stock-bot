import io
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import backtest.paper_trading_operations_console as console_module
from backtest.paper_trading_operations_console import (
    PaperTradingOperationsConsolePolicy,
    build_paper_trading_operations_console,
    load_latest_paper_trading_operations_console,
    save_paper_trading_operations_console,
    validate_console_policy,
)
from test_manual_paper_run_release_gate import (
    create_safe_v116_to_v118_chain,
    validate_successful_release,
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_safe_v116_to_v119_chain() -> tuple[
    Any,
    Any,
    Any,
    Any,
]:
    (
        orchestrator_result,
        audit_result,
        reconciliation_result,
    ) = create_safe_v116_to_v118_chain()
    release_result = run_silently(
        validate_successful_release,
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )

    for version, result in (
        ("V11.6", orchestrator_result),
        ("V11.7", audit_result),
        ("V11.8", reconciliation_result),
        ("V11.9", release_result),
    ):
        if not result.all_checks_passed:
            raise RuntimeError(
                f"{version} 테스트 Source가 안전하지 않습니다."
            )

    return (
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )


def assert_execution_safety(result: Any) -> None:
    if not result.read_only:
        raise RuntimeError(
            "Operations Console이 읽기 전용이 아닙니다."
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


def validate_ready_console(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    result = run_silently(
        build_paper_trading_operations_console,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )

    if result.version != "V12.0":
        raise RuntimeError(
            "Console Version이 V12.0이 아닙니다."
        )
    if result.console_status != "READY":
        raise RuntimeError(
            "정상 Console 상태가 READY가 아닙니다."
        )
    if result.total_card_count != 6:
        raise RuntimeError(
            "Operations Card 수가 6이 아닙니다."
        )
    if result.passed_card_count != 6:
        raise RuntimeError(
            "PASS Card 수가 6이 아닙니다."
        )
    if any(
        card.card_status != "PASS"
        for card in result.console_cards
    ):
        raise RuntimeError(
            "정상 Console Card 중 PASS가 아닌 항목이 있습니다."
        )

    expected_card_names = (
        "ORCHESTRATION",
        "AUDIT",
        "RECONCILIATION",
        "RELEASE",
        "IDENTITY",
        "EXECUTION_SAFETY",
    )
    actual_card_names = tuple(
        card.card_name
        for card in result.console_cards
    )
    if actual_card_names != expected_card_names:
        raise RuntimeError(
            "Operations Card 순서가 올바르지 않습니다."
        )
    if result.completed_stage_count != 6:
        raise RuntimeError(
            "완료 Stage 수가 6이 아닙니다."
        )
    if result.audit_entry_count != 8:
        raise RuntimeError(
            "Audit Entry 수가 8이 아닙니다."
        )
    if result.reconciliation_item_count != 50:
        raise RuntimeError(
            "Reconciliation 항목 수가 50이 아닙니다."
        )
    if result.reconciliation_mismatch_count != 0:
        raise RuntimeError(
            "정상 Console에 Reconciliation 불일치가 있습니다."
        )
    if not result.paper_run_locked:
        raise RuntimeError(
            "정상 Console의 Paper Run이 잠기지 않았습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Console의 All Checks가 실패했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_invalid_input(
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    result = run_silently(
        build_paper_trading_operations_console,
        {"version": "V11.6"},
        audit_result,
        reconciliation_result,
        release_result,
    )

    if result.console_status != "FAILED":
        raise RuntimeError(
            "잘못된 입력이 FAILED로 분류되지 않았습니다."
        )
    if result.input_checks_passed:
        raise RuntimeError(
            "잘못된 입력 검사가 통과했습니다."
        )
    if result.console_cards:
        raise RuntimeError(
            "잘못된 입력에 Console Card가 생성됐습니다."
        )

    assert_execution_safety(result)
    return result


def validate_version_review(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    wrong_version_release = replace(
        release_result,
        version="V11.8",
    )
    result = run_silently(
        build_paper_trading_operations_console,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        wrong_version_release,
    )

    if result.console_status != "REVIEW":
        raise RuntimeError(
            "Version 불일치가 REVIEW로 분류되지 않았습니다."
        )
    if result.version_checks_passed:
        raise RuntimeError(
            "Version 불일치 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_incomplete_status_review(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    incomplete_orchestrator = replace(
        orchestrator_result,
        orchestrator_status="BLOCKED",
        all_checks_passed=False,
        completed_stage_count=5,
    )
    result = run_silently(
        build_paper_trading_operations_console,
        incomplete_orchestrator,
        audit_result,
        reconciliation_result,
        release_result,
    )

    if result.console_status != "REVIEW":
        raise RuntimeError(
            "미완료 상태가 REVIEW로 분류되지 않았습니다."
        )
    if result.status_checks_passed:
        raise RuntimeError(
            "미완료 Status 검사가 통과했습니다."
        )
    if result.passed_card_count == 6:
        raise RuntimeError(
            "미완료 Console의 모든 Card가 PASS입니다."
        )

    assert_execution_safety(result)
    return result


def validate_identity_block(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    mismatched_release = replace(
        release_result,
        source_orchestration_id=(
            "different-orchestration-id"
        ),
    )
    result = run_silently(
        build_paper_trading_operations_console,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        mismatched_release,
    )

    if result.console_status != "BLOCKED":
        raise RuntimeError(
            "ID 불일치가 BLOCKED로 분류되지 않았습니다."
        )
    if result.identity_checks_passed:
        raise RuntimeError(
            "ID Chain 불일치 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_actor_block(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    mismatched_release = replace(
        release_result,
        manual_actor="different-user",
    )
    result = run_silently(
        build_paper_trading_operations_console,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        mismatched_release,
    )

    if result.console_status != "BLOCKED":
        raise RuntimeError(
            "Actor 불일치가 BLOCKED로 분류되지 않았습니다."
        )
    if result.actor_checks_passed:
        raise RuntimeError(
            "Actor Chain 불일치 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_audit_hash_failure(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    changed_entries = list(
        audit_result.audit_entries
    )
    changed_entries[3] = replace(
        changed_entries[3],
        stage_status="TAMPERED",
    )
    tampered_audit = replace(
        audit_result,
        audit_entries=tuple(changed_entries),
    )
    result = run_silently(
        build_paper_trading_operations_console,
        orchestrator_result,
        tampered_audit,
        reconciliation_result,
        release_result,
    )

    if result.console_status != "FAILED":
        raise RuntimeError(
            "Audit Hash 조작이 FAILED로 분류되지 않았습니다."
        )
    if result.hash_chain_checks_passed:
        raise RuntimeError(
            "조작된 Audit Hash 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_release_seal_failure(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    tampered_seal = replace(
        release_result.release_seal,
        release_note="MANUALLY CHANGED",
    )
    tampered_release = replace(
        release_result,
        release_seal=tampered_seal,
    )
    result = run_silently(
        build_paper_trading_operations_console,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        tampered_release,
    )

    if result.console_status != "FAILED":
        raise RuntimeError(
            "Seal 조작이 FAILED로 분류되지 않았습니다."
        )
    if result.seal_checks_passed:
        raise RuntimeError(
            "조작된 Release Seal 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_unsafe_source_failure(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    release_result: Any,
) -> Any:
    unsafe_release = replace(
        release_result,
        execution_blocked=False,
        broker_api_called=True,
    )
    result = run_silently(
        build_paper_trading_operations_console,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        unsafe_release,
    )

    if result.console_status != "FAILED":
        raise RuntimeError(
            "위험 Source가 FAILED로 분류되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험 Source Safety 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_policy_safety() -> None:
    policy = PaperTradingOperationsConsolePolicy()
    policy_valid, policy_errors = (
        validate_console_policy(policy)
    )
    if not policy_valid or policy_errors:
        raise RuntimeError(
            "기본 V12.0 Policy가 유효하지 않습니다."
        )

    unsafe_policy = replace(
        policy,
        live_execution_disabled=False,
    )
    unsafe_valid, unsafe_errors = (
        validate_console_policy(unsafe_policy)
    )
    if unsafe_valid or not unsafe_errors:
        raise RuntimeError(
            "Live 허용 Policy가 차단되지 않았습니다."
        )

    writable_policy = replace(
        policy,
        read_only_console=False,
    )
    writable_valid, writable_errors = (
        validate_console_policy(
            writable_policy
        )
    )
    if writable_valid or not writable_errors:
        raise RuntimeError(
            "쓰기 가능 Console Policy가 차단되지 않았습니다."
        )

    try:
        policy.paper_only = False
    except FrozenInstanceError:
        pass
    else:
        raise RuntimeError(
            "Operations Console Policy가 변경되었습니다."
        )


def validate_save_and_load(
    ready_result: Any,
) -> None:
    original_directory = (
        console_module
        .PAPER_TRADING_OPERATIONS_CONSOLE_OUTPUT_DIRECTORY
    )

    with TemporaryDirectory() as temporary_directory:
        console_module.PAPER_TRADING_OPERATIONS_CONSOLE_OUTPUT_DIRECTORY = (
            Path(temporary_directory)
        )

        try:
            report_path, latest_path = (
                save_paper_trading_operations_console(
                    ready_result
                )
            )
            loaded = (
                load_latest_paper_trading_operations_console()
            )
        finally:
            console_module.PAPER_TRADING_OPERATIONS_CONSOLE_OUTPUT_DIRECTORY = (
                original_directory
            )

        if not report_path.exists():
            raise RuntimeError(
                "V12.0 Report 파일이 저장되지 않았습니다."
            )
        if not latest_path.exists():
            raise RuntimeError(
                "V12.0 Latest 파일이 저장되지 않았습니다."
            )
        if loaded["version"] != "V12.0":
            raise RuntimeError(
                "복원된 Version이 V12.0이 아닙니다."
            )
        if loaded["console_status"] != "READY":
            raise RuntimeError(
                "복원된 Console 상태가 READY가 아닙니다."
            )
        if len(loaded["console_cards"]) != 6:
            raise RuntimeError(
                "복원된 Operations Card 수가 6이 아닙니다."
            )
        if loaded["read_only"] is not True:
            raise RuntimeError(
                "복원된 Console이 읽기 전용이 아닙니다."
            )


def print_validation_checks(
    checks: list[tuple[str, bool]],
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("AI STOCK BOT V12.0 PAPER TRADING OPERATIONS CONSOLE TEST")
    print("=" * line_length)
    print()
    print("V12.0 VALIDATION CHECKS")
    print("-" * line_length)

    for label, passed in checks:
        print(f"{label:<70}: {passed}")

    print("=" * line_length)


def main() -> None:
    validate_policy_safety()
    (
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    ) = create_safe_v116_to_v119_chain()

    ready_result = validate_ready_console(
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )
    invalid_input_result = validate_invalid_input(
        audit_result,
        reconciliation_result,
        release_result,
    )
    version_result = validate_version_review(
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )
    status_result = (
        validate_incomplete_status_review(
            orchestrator_result,
            audit_result,
            reconciliation_result,
            release_result,
        )
    )
    identity_result = validate_identity_block(
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )
    actor_result = validate_actor_block(
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )
    hash_result = validate_audit_hash_failure(
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )
    seal_result = validate_release_seal_failure(
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )
    unsafe_result = validate_unsafe_source_failure(
        orchestrator_result,
        audit_result,
        reconciliation_result,
        release_result,
    )
    validate_save_and_load(ready_result)

    checks = [
        (
            "Version is V12.0",
            ready_result.version == "V12.0",
        ),
        (
            "Default policy is valid",
            ready_result.policy_checks_passed,
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
            "V11.6 through V11.9 inputs were validated",
            ready_result.input_checks_passed,
        ),
        (
            "Six operations cards were created",
            ready_result.total_card_count == 6,
        ),
        (
            "All six cards passed",
            ready_result.passed_card_count == 6,
        ),
        (
            "Six stages were completed",
            ready_result.completed_stage_count == 6,
        ),
        (
            "Eight audit entries were loaded",
            ready_result.audit_entry_count == 8,
        ),
        (
            "Fifty reconciliation items were loaded",
            ready_result
            .reconciliation_item_count
            == 50,
        ),
        (
            "Paper run remains locked",
            ready_result.paper_run_locked,
        ),
        (
            "Audit hash chain passed",
            ready_result.hash_chain_checks_passed,
        ),
        (
            "Release seal passed",
            ready_result.seal_checks_passed,
        ),
        (
            "Invalid input was failed",
            invalid_input_result.console_status
            == "FAILED",
        ),
        (
            "Version mismatch requires review",
            version_result.console_status
            == "REVIEW",
        ),
        (
            "Incomplete status requires review",
            status_result.console_status
            == "REVIEW",
        ),
        (
            "Identity mismatch was blocked",
            identity_result.console_status
            == "BLOCKED",
        ),
        (
            "Actor mismatch was blocked",
            actor_result.console_status
            == "BLOCKED",
        ),
        (
            "Audit hash tampering was failed",
            hash_result.console_status
            == "FAILED",
        ),
        (
            "Release seal tampering was failed",
            seal_result.console_status
            == "FAILED",
        ),
        (
            "Unsafe source was failed",
            unsafe_result.console_status
            == "FAILED",
        ),
        (
            "Result save and load passed",
            True,
        ),
        (
            "Console remains read only",
            ready_result.read_only,
        ),
        (
            "Automatic execution remains disabled",
            not ready_result
            .automatic_execution_authorized,
        ),
        (
            "Execution remains blocked",
            ready_result.execution_blocked,
        ),
        (
            "Broker API was not called",
            not ready_result.broker_api_called,
        ),
        (
            "Broker order was not created",
            not ready_result.broker_order_created,
        ),
        (
            "Live order was not created",
            not ready_result.live_order_created,
        ),
        (
            "Live execution not authorized",
            not ready_result
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
            "V12.0 Validation Check가 실패했습니다."
        )

    print()
    print(
        "V12.0 paper trading operations console test "
        "completed successfully."
    )
    print(
        "6개 상태 Card, Source 분류, Hash와 Seal 재검사가 "
        "정상적으로 검증되었습니다."
    )
    print(
        "Console은 읽기 전용이며 실제 Broker API, 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
