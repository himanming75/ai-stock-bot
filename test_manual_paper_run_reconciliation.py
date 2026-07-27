import io
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import backtest.manual_paper_run_reconciliation as reconciliation_module
from backtest.manual_paper_run_reconciliation import (
    ManualPaperRunReconciliationPolicy,
    create_reconciliation_pair_id,
    load_latest_manual_paper_run_reconciliation,
    reconcile_manual_paper_run,
    save_manual_paper_run_reconciliation,
    validate_reconciliation_policy,
)
from test_manual_paper_run_audit_trail import (
    create_safe_v116_source,
    validate_successful_audit,
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_safe_source_pair() -> tuple[Any, Any]:
    orchestrator_result = (
        create_safe_v116_source()
    )
    audit_result = run_silently(
        validate_successful_audit,
        orchestrator_result,
    )

    if not orchestrator_result.all_checks_passed:
        raise RuntimeError(
            "V11.6 테스트 Source가 안전하지 않습니다."
        )
    if not audit_result.all_checks_passed:
        raise RuntimeError(
            "V11.7 테스트 Source가 안전하지 않습니다."
        )

    return (
        orchestrator_result,
        audit_result,
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


def validate_successful_reconciliation(
    orchestrator_result: Any,
    audit_result: Any,
) -> Any:
    result = run_silently(
        reconcile_manual_paper_run,
        orchestrator_result,
        audit_result,
    )

    if result.version != "V11.8":
        raise RuntimeError(
            "Reconciliation Version이 V11.8이 아닙니다."
        )
    if (
        result.reconciliation_status
        != "RECONCILED"
    ):
        raise RuntimeError(
            "정상 결과가 RECONCILED가 아닙니다."
        )
    if result.total_item_count != 50:
        raise RuntimeError(
            "Reconciliation 항목 수가 50이 아닙니다."
        )
    if result.matched_item_count != 50:
        raise RuntimeError(
            "일치 항목 수가 50이 아닙니다."
        )
    if result.mismatched_item_count != 0:
        raise RuntimeError(
            "정상 결과에 불일치 항목이 있습니다."
        )
    if not all(
        item.matched
        for item in result.reconciliation_items
    ):
        raise RuntimeError(
            "정상 Reconciliation Item 중 실패가 있습니다."
        )
    if (
        result.source_orchestration_id
        != orchestrator_result.orchestration_id
    ):
        raise RuntimeError(
            "Orchestration ID가 연결되지 않았습니다."
        )
    if (
        result.audit_trail_id
        != audit_result.audit_trail_id
    ):
        raise RuntimeError(
            "Audit Trail ID가 연결되지 않았습니다."
        )

    expected_pair_id = create_reconciliation_pair_id(
        orchestrator_result.orchestration_id,
        audit_result.audit_trail_id,
    )
    if (
        result.reconciliation_pair_id
        != expected_pair_id
    ):
        raise RuntimeError(
            "Reconciliation Pair ID가 올바르지 않습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Reconciliation의 All Checks가 실패했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_actor_mismatch(
    orchestrator_result: Any,
    audit_result: Any,
) -> Any:
    mismatched_audit = replace(
        audit_result,
        manual_actor="different-user",
    )
    result = run_silently(
        reconcile_manual_paper_run,
        orchestrator_result,
        mismatched_audit,
    )

    if result.reconciliation_status != "MISMATCH":
        raise RuntimeError(
            "Actor 불일치가 MISMATCH가 아닙니다."
        )
    if result.actor_checks_passed:
        raise RuntimeError(
            "Actor 불일치 검사가 통과했습니다."
        )
    if result.mismatched_item_count != 1:
        raise RuntimeError(
            "Actor 불일치 항목 수가 1이 아닙니다."
        )

    assert_execution_safety(result)
    return result


def validate_identity_mismatch(
    orchestrator_result: Any,
    audit_result: Any,
) -> Any:
    mismatched_audit = replace(
        audit_result,
        source_orchestration_id=(
            "different-orchestration-id"
        ),
    )
    result = run_silently(
        reconcile_manual_paper_run,
        orchestrator_result,
        mismatched_audit,
    )

    if result.reconciliation_status != "MISMATCH":
        raise RuntimeError(
            "Identity 불일치가 MISMATCH가 아닙니다."
        )
    if result.identity_checks_passed:
        raise RuntimeError(
            "Identity 불일치 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_stage_mismatch(
    orchestrator_result: Any,
    audit_result: Any,
) -> Any:
    changed_records = list(
        orchestrator_result.stage_records
    )
    changed_records[2] = replace(
        changed_records[2],
        result_status="MANUALLY_CHANGED",
    )
    changed_orchestrator = replace(
        orchestrator_result,
        stage_records=tuple(changed_records),
    )
    result = run_silently(
        reconcile_manual_paper_run,
        changed_orchestrator,
        audit_result,
    )

    if result.reconciliation_status != "MISMATCH":
        raise RuntimeError(
            "Stage 불일치가 MISMATCH가 아닙니다."
        )
    if result.stage_checks_passed:
        raise RuntimeError(
            "Stage 불일치 검사가 통과했습니다."
        )
    if not any(
        not item.matched
        and item.stage_name
        == "LEDGER_INTEGRATION"
        for item in result.reconciliation_items
    ):
        raise RuntimeError(
            "변경된 Ledger Stage가 표시되지 않았습니다."
        )

    assert_execution_safety(result)
    return result


def validate_hash_tampering_block(
    orchestrator_result: Any,
    audit_result: Any,
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
        reconcile_manual_paper_run,
        orchestrator_result,
        tampered_audit,
    )

    if result.reconciliation_status != "FAILED":
        raise RuntimeError(
            "Hash 조작 결과가 FAILED가 아닙니다."
        )
    if result.hash_chain_checks_passed:
        raise RuntimeError(
            "조작된 Hash Chain 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_duplicate_pair_block(
    orchestrator_result: Any,
    audit_result: Any,
    successful_result: Any,
) -> Any:
    result = run_silently(
        reconcile_manual_paper_run,
        orchestrator_result,
        audit_result,
        successful_result.reconciliation_history,
    )

    if result.reconciliation_status != "FAILED":
        raise RuntimeError(
            "중복 Pair 결과가 FAILED가 아닙니다."
        )
    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 Pair 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_unsafe_source_block(
    orchestrator_result: Any,
    audit_result: Any,
) -> Any:
    unsafe_orchestrator = replace(
        orchestrator_result,
        execution_blocked=False,
        broker_api_called=True,
    )
    result = run_silently(
        reconcile_manual_paper_run,
        unsafe_orchestrator,
        audit_result,
    )

    if result.reconciliation_status != "FAILED":
        raise RuntimeError(
            "위험한 Source 결과가 FAILED가 아닙니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Source Safety 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_invalid_version_block(
    orchestrator_result: Any,
    audit_result: Any,
) -> Any:
    invalid_audit = replace(
        audit_result,
        version="V11.6",
    )
    result = run_silently(
        reconcile_manual_paper_run,
        orchestrator_result,
        invalid_audit,
    )

    if result.reconciliation_status != "FAILED":
        raise RuntimeError(
            "잘못된 Version 결과가 FAILED가 아닙니다."
        )
    if result.input_checks_passed:
        raise RuntimeError(
            "잘못된 Version 입력 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_history_limit(
    orchestrator_result: Any,
    audit_result: Any,
) -> Any:
    existing_history = tuple(
        f"old-pair-{index:03d}"
        for index in range(100)
    )
    result = run_silently(
        reconcile_manual_paper_run,
        orchestrator_result,
        audit_result,
        existing_history,
    )

    if result.reconciliation_status != "RECONCILED":
        raise RuntimeError(
            "History 한도 검사용 대조가 실패했습니다."
        )
    if len(result.reconciliation_history) != 100:
        raise RuntimeError(
            "History 보관 개수가 100이 아닙니다."
        )
    if (
        result.reconciliation_history[-1]
        != result.reconciliation_pair_id
    ):
        raise RuntimeError(
            "최신 Pair ID가 History에 없습니다."
        )
    if (
        "old-pair-000"
        in result.reconciliation_history
    ):
        raise RuntimeError(
            "가장 오래된 History가 제거되지 않았습니다."
        )

    assert_execution_safety(result)
    return result


def validate_policy_safety() -> None:
    policy = ManualPaperRunReconciliationPolicy()
    policy_valid, policy_errors = (
        validate_reconciliation_policy(policy)
    )
    if not policy_valid or policy_errors:
        raise RuntimeError(
            "기본 V11.8 Policy가 유효하지 않습니다."
        )

    unsafe_policy = replace(
        policy,
        live_execution_disabled=False,
    )
    unsafe_valid, unsafe_errors = (
        validate_reconciliation_policy(
            unsafe_policy
        )
    )
    if unsafe_valid or not unsafe_errors:
        raise RuntimeError(
            "Live 허용 Policy가 차단되지 않았습니다."
        )

    invalid_version_policy = replace(
        policy,
        required_audit_version="V11.6",
    )
    version_valid, version_errors = (
        validate_reconciliation_policy(
            invalid_version_policy
        )
    )
    if version_valid or not version_errors:
        raise RuntimeError(
            "잘못된 Audit Version Policy가 차단되지 않았습니다."
        )

    try:
        policy.paper_only = False
    except FrozenInstanceError:
        pass
    else:
        raise RuntimeError(
            "Reconciliation Policy가 변경되었습니다."
        )


def validate_save_and_load(
    successful_result: Any,
) -> None:
    original_directory = (
        reconciliation_module
        .MANUAL_PAPER_RUN_RECONCILIATION_OUTPUT_DIRECTORY
    )

    with TemporaryDirectory() as temporary_directory:
        reconciliation_module.MANUAL_PAPER_RUN_RECONCILIATION_OUTPUT_DIRECTORY = (
            Path(temporary_directory)
        )

        try:
            report_path, latest_path = (
                save_manual_paper_run_reconciliation(
                    successful_result
                )
            )
            loaded = (
                load_latest_manual_paper_run_reconciliation()
            )
        finally:
            reconciliation_module.MANUAL_PAPER_RUN_RECONCILIATION_OUTPUT_DIRECTORY = (
                original_directory
            )

        if not report_path.exists():
            raise RuntimeError(
                "V11.8 Report 파일이 저장되지 않았습니다."
            )
        if not latest_path.exists():
            raise RuntimeError(
                "V11.8 Latest 파일이 저장되지 않았습니다."
            )
        if loaded["version"] != "V11.8":
            raise RuntimeError(
                "복원된 Version이 V11.8이 아닙니다."
            )
        if (
            loaded["reconciliation_status"]
            != "RECONCILED"
        ):
            raise RuntimeError(
                "복원된 상태가 RECONCILED가 아닙니다."
            )
        if len(
            loaded["reconciliation_items"]
        ) != 50:
            raise RuntimeError(
                "복원된 대조 항목 수가 50이 아닙니다."
            )


def print_validation_checks(
    checks: list[tuple[str, bool]],
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("AI STOCK BOT V11.8 MANUAL PAPER RUN RECONCILIATION TEST")
    print("=" * line_length)
    print()
    print("V11.8 VALIDATION CHECKS")
    print("-" * line_length)

    for label, passed in checks:
        print(f"{label:<70}: {passed}")

    print("=" * line_length)


def main() -> None:
    validate_policy_safety()
    (
        orchestrator_result,
        audit_result,
    ) = create_safe_source_pair()

    successful_result = (
        validate_successful_reconciliation(
            orchestrator_result,
            audit_result,
        )
    )
    actor_result = validate_actor_mismatch(
        orchestrator_result,
        audit_result,
    )
    identity_result = validate_identity_mismatch(
        orchestrator_result,
        audit_result,
    )
    stage_result = validate_stage_mismatch(
        orchestrator_result,
        audit_result,
    )
    hash_result = validate_hash_tampering_block(
        orchestrator_result,
        audit_result,
    )
    duplicate_result = validate_duplicate_pair_block(
        orchestrator_result,
        audit_result,
        successful_result,
    )
    unsafe_result = validate_unsafe_source_block(
        orchestrator_result,
        audit_result,
    )
    invalid_version_result = (
        validate_invalid_version_block(
            orchestrator_result,
            audit_result,
        )
    )
    history_result = validate_history_limit(
        orchestrator_result,
        audit_result,
    )
    validate_save_and_load(successful_result)

    checks = [
        (
            "Version is V11.8",
            successful_result.version == "V11.8",
        ),
        (
            "Default policy is valid",
            successful_result.policy_checks_passed,
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
            "V11.6 and V11.7 inputs were validated",
            successful_result.input_checks_passed,
        ),
        (
            "Fifty reconciliation items were created",
            successful_result.total_item_count
            == 50,
        ),
        (
            "All fifty items matched",
            successful_result.matched_item_count
            == 50,
        ),
        (
            "Identity checks passed",
            successful_result
            .identity_checks_passed,
        ),
        (
            "Actor checks passed",
            successful_result.actor_checks_passed,
        ),
        (
            "Status checks passed",
            successful_result.status_checks_passed,
        ),
        (
            "Six stage checks passed",
            successful_result.stage_checks_passed,
        ),
        (
            "SHA-256 hash chain was revalidated",
            successful_result
            .hash_chain_checks_passed,
        ),
        (
            "Actor mismatch was detected",
            actor_result.reconciliation_status
            == "MISMATCH",
        ),
        (
            "Identity mismatch was detected",
            identity_result.reconciliation_status
            == "MISMATCH",
        ),
        (
            "Stage mismatch was detected",
            stage_result.reconciliation_status
            == "MISMATCH",
        ),
        (
            "Hash tampering was blocked",
            hash_result.reconciliation_status
            == "FAILED",
        ),
        (
            "Duplicate pair was blocked",
            duplicate_result.reconciliation_status
            == "FAILED",
        ),
        (
            "Unsafe source was blocked",
            unsafe_result.reconciliation_status
            == "FAILED",
        ),
        (
            "Invalid version was blocked",
            invalid_version_result
            .reconciliation_status
            == "FAILED",
        ),
        (
            "History was trimmed to 100 records",
            len(
                history_result
                .reconciliation_history
            )
            == 100,
        ),
        (
            "Result save and load passed",
            True,
        ),
        (
            "Automatic execution remains disabled",
            not successful_result
            .automatic_execution_authorized,
        ),
        (
            "Execution remains blocked",
            successful_result.execution_blocked,
        ),
        (
            "Broker API was not called",
            not successful_result.broker_api_called,
        ),
        (
            "Broker order was not created",
            not successful_result
            .broker_order_created,
        ),
        (
            "Live order was not created",
            not successful_result.live_order_created,
        ),
        (
            "Live execution not authorized",
            not successful_result
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
            "V11.8 Validation Check가 실패했습니다."
        )

    print()
    print(
        "V11.8 manual paper run reconciliation test "
        "completed successfully."
    )
    print(
        "50개 대조 항목, 불일치 분류, Hash 재검사 및 "
        "중복 방지가 정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
